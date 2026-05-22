import hashlib
import logging

import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from base.serializers import UserSerializer, UserSerializerWithToken

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GENERIC_RESET_MESSAGE = (
    "If an account exists with this email, a password reset link has been sent."
)
PWD_RESET_RATE_SECONDS = 60 * 15
PWD_RESET_RATE_MAX = 3

activation_token = PasswordResetTokenGenerator()
password_reset_token = PasswordResetTokenGenerator()


# --- JWT login ---


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        serializer = UserSerializerWithToken(self.user).data
        for k, v in serializer.items():
            data[k] = v
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# --- Google Sign-In helpers ---


def _verify_google_id_token(id_token: str) -> dict:
    client_id = (getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or "").strip()
    if not client_id:
        raise ValueError("Google sign-in is not configured on the server.")

    try:
        response = requests.get(
            GOOGLE_TOKEN_INFO_URL,
            params={"id_token": id_token},
            timeout=8,
        )
    except requests.RequestException as exc:
        logger.warning("Google tokeninfo request failed: %s", exc)
        raise ValueError("Could not verify Google sign-in. Try again.") from exc

    if response.status_code != 200:
        raise ValueError("Invalid or expired Google sign-in.")

    claims = response.json()
    if claims.get("aud") != client_id:
        raise ValueError("Google token audience mismatch.")
    if claims.get("email_verified") not in ("true", True):
        raise ValueError("Google email is not verified.")

    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Google account has no email.")

    return {
        "email": email,
        "given_name": claims.get("given_name") or "",
        "name": claims.get("name") or "",
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def googleAuth(request):
    credential = (request.data.get("credential") or "").strip()
    if not credential:
        return Response(
            {"detail": "Google credential is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        profile = _verify_google_id_token(credential)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    email = profile["email"]
    user = User.objects.filter(email__iexact=email).first()

    if user:
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
    else:
        user = User(
            username=email,
            email=email,
            first_name=profile.get("given_name") or profile.get("name") or "",
            is_active=True,
        )
        user.set_unusable_password()
        user.save()

    return Response(UserSerializerWithToken(user, many=False).data)


# --- Password reset helpers ---


def _pwd_reset_rate_key(email: str) -> str:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    return f"pwd_reset_rate:{digest}"


def _send_password_reset_email(user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_reset_token.make_token(user)
    reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

    send_mail(
        subject="Reset your Electrovix password",
        message=(
            f"Hi {user.first_name or user.username},\n\n"
            f"Click the link below to reset your password (expires in 24 hours):\n"
            f"{reset_link}\n\n"
            f"If you did not request this, ignore this email.\n\n"
            f"— Electrovix"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def requestPasswordReset(request):
    email = (request.data.get("email") or "").strip().lower()

    if email:
        key = _pwd_reset_rate_key(email)
        count = cache.get(key, 0)
        if count < PWD_RESET_RATE_MAX:
            cache.set(key, count + 1, PWD_RESET_RATE_SECONDS)
            user = User.objects.filter(email__iexact=email).first()
            if user and user.is_active:
                try:
                    _send_password_reset_email(user)
                except Exception:
                    logger.exception("Password reset email failed for user id=%s", user.pk)

    return Response({"detail": GENERIC_RESET_MESSAGE}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def confirmPasswordReset(request):
    uid = request.data.get("uid", "")
    token = request.data.get("token", "")
    password = request.data.get("password", "")

    if not uid or not token or not password:
        return Response(
            {"detail": "uid, token, and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {"detail": "Password must be at least 8 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return Response(
            {"detail": "Invalid or expired reset link."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.is_active or not password_reset_token.check_token(user, token):
        return Response(
            {"detail": "Invalid or expired reset link."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(password)
    user.save(update_fields=["password"])

    return Response(
        {"detail": "Password reset successful. You can sign in now."},
        status=status.HTTP_200_OK,
    )


# --- Register / activate ---


@api_view(["POST"])
def registerUser(request):
    data = request.data
    try:
        if not data.get("name") or not data.get("email") or not data.get("password"):
            return Response(
                {"detail": "Name, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=data["email"]).exists():
            return Response(
                {"detail": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create(
            first_name=data["name"],
            username=data["email"],
            email=data["email"],
            password=make_password(data["password"]),
            is_active=False,
        )

        token = activation_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = f"{settings.FRONTEND_URL}/activate/{uid}/{token}"

        send_mail(
            "Activate Your Account",
            f"Hi {user.first_name},\n\nPlease click the link below to activate your account:\n{activation_link}",
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        return Response(
            {"detail": "Account created successfully. Please check your email to activate your account."},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error("Error during registration: %s", e)
        return Response(
            {"detail": "An error occurred during registration. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def activateUser(request, uid, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)

        if activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return Response(
                {"detail": "Account activated successfully. Please log in."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Invalid or expired activation link."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except User.DoesNotExist:
        return Response(
            {"detail": "Invalid activation link. User does not exist."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error("Error during activation: %s", e)
        return Response(
            {"detail": "An error occurred during activation. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# --- Profile / admin ---


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getUserProfile(request):
    return Response(UserSerializer(request.user, many=False).data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def updateUserProfile(request):
    user = request.user
    data = request.data
    user.first_name = data["name"]
    user.username = data["email"]
    user.email = data["email"]

    if data["password"] != "":
        user.password = make_password(data["password"])

    user.save()
    return Response(UserSerializerWithToken(user, many=False).data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def getUsers(request):
    return Response(UserSerializer(User.objects.all(), many=True).data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def getUserById(request, pk):
    user = User.objects.get(id=pk)
    return Response(UserSerializer(user, many=False).data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def updateUser(request, pk):
    user = User.objects.get(id=pk)
    data = request.data

    user.first_name = data["name"]
    user.username = data["email"]
    user.email = data["email"]
    user.is_staff = data["isAdmin"]
    user.save()

    return Response(UserSerializer(user, many=False).data)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def deleteUser(request, pk):
    User.objects.get(id=pk).delete()
    return Response("User was deleted")
