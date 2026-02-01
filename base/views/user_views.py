from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from django.contrib.auth.models import User
from base.serializers import ProductSerializer, UserSerializer, UserSerializerWithToken
# Create your views here.
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from django.contrib.auth.hashers import make_password
from rest_framework import status
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from base.serializers import UserSerializerWithToken
from rest_framework import status
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
import logging

logger = logging.getLogger(__name__)  # Set up logging for debugging

# Custom token generator
class ActivationTokenGenerator(PasswordResetTokenGenerator):
    pass

activation_token = ActivationTokenGenerator()


# for login. 
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)


        serializer = UserSerializerWithToken(self.user).data
        for k, v in serializer.items():
            data[k] = v

        return data
    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    
# Register User
@api_view(['POST'])
def registerUser(request):
    data = request.data
    try:
        # Validate input data
        if not data.get('name') or not data.get('email') or not data.get('password'):
            return Response(
                {"detail": "Name, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user already exists
        if User.objects.filter(email=data['email']).exists():
            return Response(
                {"detail": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create inactive user
        user = User.objects.create(
            first_name=data['name'],
            username=data['email'],
            email=data['email'],
            password=make_password(data['password']),
            is_active=False,
        )

        # Generate activation token
        token = activation_token.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Activation link
        activation_link = f"https://electrovix.netlify.app/activate/{uid}/{token}"


        # Send activation email
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
        logger.error(f"Error during registration: {e}")  # Log the error for debugging
        return Response(
            {"detail": "An error occurred during registration. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Activate User
@api_view(['GET'])
def activateUser(request, uid, token):
    try:
        # Decode the user ID
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)

        # Validate the token
        if activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return Response(
                {"detail": "Account activated successfully. Please log in."},
                status=status.HTTP_200_OK,
            )
        else:
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
        logger.error(f"Error during activation: {e}")  # Log the error for debugging
        return Response(
            {"detail": "An error occurred during activation. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserProfile(request):
    user=request.user

    serializer=UserSerializer(user,many=False)
    return Response(serializer.data)





@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateUserProfile(request):
    user = request.user
    serializer = UserSerializerWithToken(user, many=False)
    data = request.data
    user.first_name = data['name']
    user.username = data['email']
    user.email = data['email']

    if data['password'] != '':
        user.password = make_password(data['password'])

    user.save()

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUsers(request):
    users= User.objects.all()
    serializer=UserSerializer(users,many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUserById(request, pk):
    user = User.objects.get(id=pk)
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateUser(request, pk):
    user = User.objects.get(id=pk)

    data = request.data

    user.first_name = data['name']
    user.username = data['email']
    user.email = data['email']
    user.is_staff = data['isAdmin']

    user.save()

    serializer = UserSerializer(user, many=False)

    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteUser(request, pk):
    userForDeletion = User.objects.get(id=pk)
    userForDeletion.delete()
    return Response('User was deleted')
 

