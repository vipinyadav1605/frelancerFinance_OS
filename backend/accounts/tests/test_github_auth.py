from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services.github_auth import get_or_create_user_from_github


class GetOrCreateUserFromGitHubTests(TestCase):
    def test_creates_a_new_user_with_an_unusable_password(self):
        user = get_or_create_user_from_github("new@example.com", "New Person")
        self.assertEqual(user.name, "New Person")
        self.assertFalse(user.has_usable_password())

    def test_reuses_an_existing_account_with_the_same_email(self):
        existing = User.objects.create_user(email="riya@example.com", password="testpass123")
        user = get_or_create_user_from_github("riya@example.com", "Riya")
        self.assertEqual(user.pk, existing.pk)


class GitHubLoginViewTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters (shared "login" scope) live in the cache
        self.api = APIClient()

    @override_settings(GITHUB_OAUTH_CLIENT_ID="", GITHUB_OAUTH_CLIENT_SECRET="")
    def test_returns_503_when_not_configured(self):
        response = self.api.post("/api/auth/github/", {"code": "whatever"})
        self.assertEqual(response.status_code, 503)

    @override_settings(GITHUB_OAUTH_CLIENT_ID="id123", GITHUB_OAUTH_CLIENT_SECRET="secret123")
    @patch("accounts.services.github_auth.requests.get")
    @patch("accounts.services.github_auth.requests.post")
    def test_valid_code_returns_jwt_pair_and_creates_user(self, mock_post, mock_get):
        mock_post.return_value = MagicMock(ok=True, json=lambda: {"access_token": "gho_test"})
        mock_get.return_value = MagicMock(
            ok=True, json=lambda: {"email": "new@example.com", "name": "New Person", "login": "newperson"},
        )
        response = self.api.post("/api/auth/github/", {"code": "abc123"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    @override_settings(GITHUB_OAUTH_CLIENT_ID="id123", GITHUB_OAUTH_CLIENT_SECRET="secret123")
    @patch("accounts.services.github_auth.requests.get")
    @patch("accounts.services.github_auth.requests.post")
    def test_falls_back_to_verified_primary_email_when_profile_email_is_private(self, mock_post, mock_get):
        mock_post.return_value = MagicMock(ok=True, json=lambda: {"access_token": "gho_test"})
        user_response = MagicMock(ok=True, json=lambda: {"email": None, "name": "New Person", "login": "newperson"})
        emails_response = MagicMock(ok=True, json=lambda: [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ])
        mock_get.side_effect = [user_response, emails_response]
        response = self.api.post("/api/auth/github/", {"code": "abc123"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="primary@example.com").exists())

    @override_settings(GITHUB_OAUTH_CLIENT_ID="id123", GITHUB_OAUTH_CLIENT_SECRET="secret123")
    @patch("accounts.services.github_auth.requests.post")
    def test_invalid_code_returns_401(self, mock_post):
        mock_post.return_value = MagicMock(ok=False, json=lambda: {})
        response = self.api.post("/api/auth/github/", {"code": "bad-code"})
        self.assertEqual(response.status_code, 401)

    @override_settings(GITHUB_OAUTH_CLIENT_ID="id123", GITHUB_OAUTH_CLIENT_SECRET="secret123")
    @patch("accounts.services.github_auth.requests.get")
    @patch("accounts.services.github_auth.requests.post")
    def test_no_verified_email_available_returns_401(self, mock_post, mock_get):
        mock_post.return_value = MagicMock(ok=True, json=lambda: {"access_token": "gho_test"})
        user_response = MagicMock(ok=True, json=lambda: {"email": None, "name": "New Person", "login": "newperson"})
        emails_response = MagicMock(ok=True, json=lambda: [{"email": "unverified@example.com", "primary": True, "verified": False}])
        mock_get.side_effect = [user_response, emails_response]
        response = self.api.post("/api/auth/github/", {"code": "abc123"})
        self.assertEqual(response.status_code, 401)
