from unittest.mock import Mock, patch

from django.core import mail
from django.test import TestCase

from accounts.models import NotificationPreference, User
from integrations.models import WebhookDelivery, WebhookSubscription
from integrations.services.webhooks import send_webhook_event
from notifications.models import Notification


class SendWebhookEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")

    @patch("integrations.services.webhooks.assert_safe_webhook_url")
    @patch("integrations.services.webhooks.requests.post")
    def test_delivers_to_active_subscription_for_matching_event(self, mock_post, mock_safe):
        mock_post.return_value = Mock(status_code=200, ok=True)
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.paid", secret="s3cr3t",
        )
        send_webhook_event(self.user, "invoice.paid", {"invoice_number": "INV-1"})
        mock_post.assert_called_once()
        delivery = WebhookDelivery.objects.get()
        self.assertTrue(delivery.success)
        self.assertEqual(delivery.status_code, 200)

    @patch("integrations.services.webhooks.requests.post")
    def test_does_not_deliver_to_subscription_for_a_different_event(self, mock_post):
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="expense.created", secret="s3cr3t",
        )
        send_webhook_event(self.user, "invoice.paid", {"invoice_number": "INV-1"})
        mock_post.assert_not_called()

    @patch("integrations.services.webhooks.requests.post")
    def test_does_not_deliver_to_inactive_subscription(self, mock_post):
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.paid",
            secret="s3cr3t", is_active=False,
        )
        send_webhook_event(self.user, "invoice.paid", {"invoice_number": "INV-1"})
        mock_post.assert_not_called()

    @patch("integrations.services.webhooks.assert_safe_webhook_url")
    @patch("integrations.services.webhooks.requests.post")
    def test_request_exception_is_caught_and_logged_as_a_failed_delivery(self, mock_post, mock_safe):
        import requests
        mock_post.side_effect = requests.ConnectionError("refused")
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.paid", secret="s3cr3t",
        )
        send_webhook_event(self.user, "invoice.paid", {"invoice_number": "INV-1"})  # must not raise
        delivery = WebhookDelivery.objects.get()
        self.assertFalse(delivery.success)
        self.assertIn("refused", delivery.error_message)

        self.assertTrue(Notification.objects.filter(user=self.user, notification_type="webhook_failed").exists())
        self.assertEqual(len(mail.outbox), 1)

    @patch("integrations.services.webhooks.assert_safe_webhook_url")
    @patch("integrations.services.webhooks.requests.post")
    def test_failure_alert_email_is_skipped_when_preference_is_off(self, mock_post, mock_safe):
        import requests
        mock_post.side_effect = requests.ConnectionError("refused")
        NotificationPreference.objects.filter(user=self.user).update(webhook_failure_emails=False)
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.paid", secret="s3cr3t",
        )
        send_webhook_event(self.user, "invoice.paid", {"invoice_number": "INV-1"})
        self.assertEqual(len(mail.outbox), 0)
        # In-app notification still fires even when the email alert is muted.
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type="webhook_failed").exists())

    @patch("integrations.services.webhooks.assert_safe_webhook_url")
    @patch("integrations.services.webhooks.requests.post")
    def test_request_is_signed_with_the_subscription_secret(self, mock_post, mock_safe):
        mock_post.return_value = Mock(status_code=200, ok=True)
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.paid", secret="s3cr3t",
        )
        send_webhook_event(self.user, "invoice.paid", {"invoice_number": "INV-1"})
        _, kwargs = mock_post.call_args
        self.assertIn("X-Ffos-Signature", kwargs["headers"])
