from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services.google_auth import get_or_create_user_from_google


class GetOrCreateUserFromGoogleTests(TestCase):
    def test_creates_a_new_user_with_an_unusable_password(self):
        user = get_or_create_user_from_google("new@example.com", "New Person")
        self.assertEqual(user.name, "New Person")
        self.assertFalse(user.has_usable_password())

    def test_reuses_an_existing_account_with_the_same_email(self):
        existing = User.objects.create_user(email="riya@example.com", password="testpass123")
        user = get_or_create_user_from_google("riya@example.com", "Riya")
        self.assertEqual(user.pk, existing.pk)
        self.assertTrue(user.has_usable_password())  # existing password-based account untouched

    def test_email_match_is_case_insensitive(self):
        existing = User.objects.create_user(email="Riya@Example.com", password="testpass123")
        user = get_or_create_user_from_google("riya@example.com", "Riya")
        self.assertEqual(user.pk, existing.pk)


class GoogleLoginViewTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_returns_503_when_not_configured(self):
        response = self.api.post("/api/auth/google/", {"id_token": "whatever"})
        self.assertEqual(response.status_code, 503)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="fake-client-id")
    @patch("accounts.services.google_auth.google_id_token.verify_oauth2_token")
    def test_valid_token_returns_jwt_pair_and_creates_user(self, mock_verify):
        mock_verify.return_value = {"email": "new@example.com", "name": "New Person"}
        response = self.api.post("/api/auth/google/", {"id_token": "real-looking-token"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="fake-client-id")
    @patch("accounts.services.google_auth.google_id_token.verify_oauth2_token")
    def test_invalid_token_returns_401(self, mock_verify):
        mock_verify.side_effect = ValueError("Token is invalid")
        response = self.api.post("/api/auth/google/", {"id_token": "garbage"})
        self.assertEqual(response.status_code, 401)
