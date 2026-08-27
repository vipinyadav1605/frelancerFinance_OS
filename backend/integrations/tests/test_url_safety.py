import socket
from unittest.mock import patch

from django.test import TestCase

from integrations.services.url_safety import UnsafeWebhookUrlError, assert_safe_webhook_url


def _resolved(*ips):
    """Builds a fake getaddrinfo() return value resolving to the given IPv4 addresses."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ips]


class AssertSafeWebhookUrlTests(TestCase):
    @patch("integrations.services.url_safety.socket.getaddrinfo")
    def test_public_https_url_is_allowed(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _resolved("93.184.216.34")  # a real public IP (example.com)
        assert_safe_webhook_url("https://example.com/hook")  # must not raise

    def test_localhost_is_rejected(self):
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("http://localhost/hook")

    @patch("integrations.services.url_safety.socket.getaddrinfo")
    def test_loopback_ip_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _resolved("127.0.0.1")
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("http://127.0.0.1/hook")

    @patch("integrations.services.url_safety.socket.getaddrinfo")
    def test_private_network_ip_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _resolved("192.168.1.5")
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("http://internal.example.com/hook")

    @patch("integrations.services.url_safety.socket.getaddrinfo")
    def test_cloud_metadata_link_local_ip_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = _resolved("169.254.169.254")
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("http://metadata.example.com/latest/meta-data/")

    @patch("integrations.services.url_safety.socket.getaddrinfo")
    def test_a_hostname_resolving_to_one_safe_and_one_unsafe_ip_is_rejected(self, mock_getaddrinfo):
        # DNS rebinding style: if ANY resolved address is unsafe, reject the whole thing.
        mock_getaddrinfo.return_value = _resolved("93.184.216.34", "127.0.0.1")
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("http://mixed.example.com/hook")

    def test_non_http_scheme_is_rejected(self):
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("file:///etc/passwd")

    def test_missing_hostname_is_rejected(self):
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("https:///no-host")

    @patch("integrations.services.url_safety.socket.getaddrinfo")
    def test_unresolvable_hostname_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
        with self.assertRaises(UnsafeWebhookUrlError):
            assert_safe_webhook_url("http://this-host-does-not-exist.invalid/hook")


class WebhookSubscriptionApiValidationTests(TestCase):
    def setUp(self):
        from accounts.models import User
        from rest_framework.test import APIClient
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    @patch("integrations.serializers.assert_safe_webhook_url")
    def test_creating_a_subscription_with_a_private_url_is_rejected(self, mock_assert_safe):
        mock_assert_safe.side_effect = UnsafeWebhookUrlError("not safe")
        response = self.api.post("/api/webhooks/", {"url": "http://127.0.0.1:8000/hook", "event": "invoice.paid"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("url", response.data)

    @patch("integrations.serializers.assert_safe_webhook_url")
    def test_creating_a_subscription_with_a_public_url_succeeds(self, mock_assert_safe):
        mock_assert_safe.return_value = None
        response = self.api.post("/api/webhooks/", {"url": "https://example.com/hook", "event": "invoice.paid"})
        self.assertEqual(response.status_code, 201)
