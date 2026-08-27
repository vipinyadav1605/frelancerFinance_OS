from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import BusinessProfile, User
from clients.models import Client
from integrations.models import WebhookDelivery, WebhookSubscription
from invoicing.models import Invoice, InvoiceStatus, TaxType


class InvoiceLifecycleWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        self.invoice = Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("10000"), cgst_amount=Decimal("900"),
            sgst_amount=Decimal("900"), total_amount=Decimal("11800"), status=InvoiceStatus.SENT,
        )
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.paid", secret="s3cr3t",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    @patch("invoicing.views.send_webhook_event")
    def test_mark_paid_fires_invoice_paid_webhook(self, mock_send):
        response = self.api.post(f"/api/invoices/{self.invoice.id}/mark-paid/", {
            "amount": "11800.00", "payment_date": timezone.now().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertEqual(args[0], self.user)
        self.assertEqual(args[1], "invoice.paid")

    @patch("integrations.services.webhooks.assert_safe_webhook_url")
    @patch("requests.post")
    def test_update_overdue_invoices_fires_invoice_overdue_webhook(self, mock_post, mock_safe):
        mock_post.return_value = Mock(status_code=200, ok=True)
        WebhookSubscription.objects.create(
            user=self.user, url="https://example.com/hook", event="invoice.overdue", secret="s3cr3t",
        )
        self.invoice.due_date = date(2020, 1, 1)
        self.invoice.save()

        from django.core.management import call_command
        call_command("update_overdue_invoices")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.OVERDUE)
        delivery = WebhookDelivery.objects.filter(event="invoice.overdue").first()
        self.assertIsNotNone(delivery)
        self.assertTrue(delivery.success)
