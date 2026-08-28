from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import BusinessProfile, User
from billing.models import FREE_TIER_MONTHLY_INVOICE_LIMIT, Subscription, SubscriptionStatus
from billing.services.limits import can_create_invoice, is_pro, usage_summary
from clients.models import Client
from invoicing.models import Invoice, TaxType


class LimitsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")

    def _create_invoice(self, n):
        return Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number=f"TEST-{n}", issue_date=date.today(), due_date=date.today(),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("100"), total_amount=Decimal("100"),
        )

    def test_free_user_is_not_pro(self):
        self.assertFalse(is_pro(self.user))

    def test_pro_user_with_active_subscription(self):
        Subscription.objects.create(user=self.user, status=SubscriptionStatus.ACTIVE)
        self.assertTrue(is_pro(self.user))

    def test_cancelled_subscription_is_not_pro(self):
        Subscription.objects.create(user=self.user, status=SubscriptionStatus.CANCELLED)
        self.assertFalse(is_pro(self.user))

    def test_free_user_can_create_invoices_up_to_the_limit(self):
        # Checked BEFORE each creation, same order InvoiceViewSet.create() uses.
        for i in range(FREE_TIER_MONTHLY_INVOICE_LIMIT):
            self.assertTrue(can_create_invoice(self.user))
            self._create_invoice(i)
        self.assertFalse(can_create_invoice(self.user))

    def test_pro_user_has_no_limit(self):
        Subscription.objects.create(user=self.user, status=SubscriptionStatus.ACTIVE)
        for i in range(FREE_TIER_MONTHLY_INVOICE_LIMIT + 5):
            self._create_invoice(i)
        self.assertTrue(can_create_invoice(self.user))

    def test_usage_summary_shape(self):
        summary = usage_summary(self.user)
        self.assertEqual(summary["free_tier_monthly_invoice_limit"], FREE_TIER_MONTHLY_INVOICE_LIMIT)
        self.assertEqual(summary["invoices_this_month"], 0)
        self.assertFalse(summary["is_pro"])


class InvoiceCreationLimitApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _create_invoice_payload(self):
        return {
            "client": self.client_obj.id, "issue_date": "2026-06-10", "due_date": "2026-06-24",
            "currency": "INR", "exchange_rate_to_inr": "1",
            "items": [{"description": "Work", "quantity": "1", "unit_price": "1000", "tax_rate_percent": "18"}],
        }

    def test_free_tier_blocks_the_sixth_invoice_this_month(self):
        for _ in range(FREE_TIER_MONTHLY_INVOICE_LIMIT):
            response = self.api.post("/api/invoices/", self._create_invoice_payload(), format="json")
            self.assertEqual(response.status_code, 201)

        blocked = self.api.post("/api/invoices/", self._create_invoice_payload(), format="json")
        self.assertEqual(blocked.status_code, 402)
        self.assertTrue(blocked.data["upgrade_required"])

    def test_pro_user_is_not_blocked(self):
        Subscription.objects.create(user=self.user, status=SubscriptionStatus.ACTIVE)
        for _ in range(FREE_TIER_MONTHLY_INVOICE_LIMIT + 2):
            response = self.api.post("/api/invoices/", self._create_invoice_payload(), format="json")
            self.assertEqual(response.status_code, 201)


class BillingStatusApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_status_endpoint(self):
        response = self.api.get("/api/billing/status/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_pro"])


class SubscribeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    @override_settings(RAZORPAY_PRO_MONTHLY_PLAN_ID="")
    def test_returns_503_when_not_configured(self):
        response = self.api.post("/api/billing/subscribe/")
        self.assertEqual(response.status_code, 503)

    @override_settings(RAZORPAY_PRO_MONTHLY_PLAN_ID="plan_test123")
    @patch("billing.views.create_subscription")
    def test_creates_a_pending_subscription_record(self, mock_create):
        mock_create.return_value = {"id": "sub_test123", "short_url": "https://rzp.io/sub_test123"}
        response = self.api.post("/api/billing/subscribe/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["short_url"], "https://rzp.io/sub_test123")
        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.razorpay_subscription_id, "sub_test123")
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)  # not active until webhook confirms payment


class SubscriptionWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.subscription = Subscription.objects.create(
            user=self.user, razorpay_subscription_id="sub_test123", status=SubscriptionStatus.CANCELLED,
        )

    @patch("invoicing.views.verify_webhook_signature")
    def test_subscription_activated_event_marks_it_active(self, mock_verify):
        mock_verify.return_value = True
        api = APIClient()
        payload = {
            "event": "subscription.activated",
            "payload": {"subscription": {"entity": {"id": "sub_test123", "current_end": 1893456000}}},
        }
        response = api.post("/api/webhooks/razorpay/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, SubscriptionStatus.ACTIVE)

    @patch("invoicing.views.verify_webhook_signature")
    def test_subscription_cancelled_event_marks_it_cancelled(self, mock_verify):
        mock_verify.return_value = True
        self.subscription.status = SubscriptionStatus.ACTIVE
        self.subscription.save()
        api = APIClient()
        payload = {
            "event": "subscription.cancelled",
            "payload": {"subscription": {"entity": {"id": "sub_test123"}}},
        }
        response = api.post("/api/webhooks/razorpay/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, SubscriptionStatus.CANCELLED)
