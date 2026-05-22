from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from base.views.user_views import password_reset_token


class GoogleAuthTests(APITestCase):
    @patch("base.views.user_views._verify_google_id_token")
    def test_google_auth_creates_user_and_returns_token(self, mock_verify):
        mock_verify.return_value = {
            "email": "newgoogle@test.com",
            "name": "New User",
            "given_name": "New",
        }

        response = self.client.post(
            reverse("google-auth"),
            {"credential": "fake-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertTrue(User.objects.filter(email="newgoogle@test.com").exists())


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reset@test.com",
            email="reset@test.com",
            password="oldpass12345",
            is_active=True,
        )

    @patch("base.views.user_views.send_mail")
    def test_password_reset_same_response_for_unknown_email(self, mock_send_mail):
        known = self.client.post(
            reverse("password-reset"),
            {"email": "reset@test.com"},
            format="json",
        )
        unknown = self.client.post(
            reverse("password-reset"),
            {"email": "nobody@test.com"},
            format="json",
        )

        self.assertEqual(known.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown.status_code, status.HTTP_200_OK)
        self.assertEqual(known.data["detail"], unknown.data["detail"])
        mock_send_mail.assert_called_once()

    def test_password_reset_confirm(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = password_reset_token.make_token(self.user)

        response = self.client.post(
            reverse("password-reset-confirm"),
            {"uid": uid, "token": token, "password": "newpass12345"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass12345"))
