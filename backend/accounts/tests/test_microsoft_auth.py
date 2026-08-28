from unittest.mock import MagicMock, patch

import jwt
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services.microsoft_auth import get_or_create_user_from_microsoft


class GetOrCreateUserFromMicrosoftTests(TestCase):
    def test_creates_a_new_user_with_an_unusable_password(self):
        user = get_or_create_user_from_microsoft("new@example.com", "New Person")
        self.assertEqual(user.name, "New Person")
        self.assertFalse(user.has_usable_password())

    def test_reuses_an_existing_account_with_the_same_email(self):
        existing = User.objects.create_user(email="riya@example.com", password="testpass123")
        user = get_or_create_user_from_microsoft("riya@example.com", "Riya")
        self.assertEqual(user.pk, existing.pk)
        self.assertTrue(user.has_usable_password())  # existing password-based account untouched


class MicrosoftLoginViewTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters (shared "login" scope) live in the cache
        self.api = APIClient()

    @override_settings(MICROSOFT_OAUTH_CLIENT_ID="")
    def test_returns_503_when_not_configured(self):
        response = self.api.post("/api/auth/microsoft/", {"id_token": "whatever"})
        self.assertEqual(response.status_code, 503)

    @override_settings(MICROSOFT_OAUTH_CLIENT_ID="fake-client-id")
    @patch("accounts.services.microsoft_auth.jwt.decode")
    @patch("accounts.services.microsoft_auth._get_jwk_client")
    def test_valid_token_returns_jwt_pair_and_creates_user(self, mock_get_client, mock_decode):
        mock_get_client.return_value.get_signing_key_from_jwt.return_value = MagicMock(key="fake-key")
        mock_decode.return_value = {
            "email": "new@example.com", "name": "New Person",
            "iss": "https://login.microsoftonline.com/some-tenant-id/v2.0",
        }
        response = self.api.post("/api/auth/microsoft/", {"id_token": "real-looking-token"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    @override_settings(MICROSOFT_OAUTH_CLIENT_ID="fake-client-id")
    @patch("accounts.services.microsoft_auth.jwt.decode")
    @patch("accounts.services.microsoft_auth._get_jwk_client")
    def test_invalid_token_returns_401(self, mock_get_client, mock_decode):
        mock_get_client.return_value.get_signing_key_from_jwt.return_value = MagicMock(key="fake-key")
        mock_decode.side_effect = jwt.InvalidTokenError("Token is invalid")
        response = self.api.post("/api/auth/microsoft/", {"id_token": "garbage"})
        self.assertEqual(response.status_code, 401)

    @override_settings(MICROSOFT_OAUTH_CLIENT_ID="fake-client-id")
    @patch("accounts.services.microsoft_auth.jwt.decode")
    @patch("accounts.services.microsoft_auth._get_jwk_client")
    def test_token_from_an_unexpected_issuer_is_rejected(self, mock_get_client, mock_decode):
        mock_get_client.return_value.get_signing_key_from_jwt.return_value = MagicMock(key="fake-key")
        mock_decode.return_value = {"email": "x@example.com", "name": "X", "iss": "https://evil.example.com/"}
        response = self.api.post("/api/auth/microsoft/", {"id_token": "garbage"})
        self.assertEqual(response.status_code, 401)

    @override_settings(MICROSOFT_OAUTH_CLIENT_ID="fake-client-id")
    @patch("accounts.services.microsoft_auth.jwt.decode")
    @patch("accounts.services.microsoft_auth._get_jwk_client")
    def test_falls_back_to_preferred_username_when_email_claim_is_missing(self, mock_get_client, mock_decode):
        mock_get_client.return_value.get_signing_key_from_jwt.return_value = MagicMock(key="fake-key")
        mock_decode.return_value = {
            "preferred_username": "amit@example.com", "name": "Amit",
            "iss": "https://login.microsoftonline.com/some-tenant-id/v2.0",
        }
        response = self.api.post("/api/auth/microsoft/", {"id_token": "real-looking-token"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="amit@example.com").exists())
