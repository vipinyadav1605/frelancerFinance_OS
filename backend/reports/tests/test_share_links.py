from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import BusinessProfile, User
from clients.models import Client
from invoicing.models import Invoice, InvoiceStatus, TaxType
from reports.models import ReportShareLink


class ReportShareLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("10000"), cgst_amount=Decimal("900"),
            sgst_amount=Decimal("900"), total_amount=Decimal("11800"),
            status=InvoiceStatus.PAID, paid_at=timezone.make_aware(timezone.datetime(2026, 6, 15)),
        )
        self.api = APIClient()

    def test_creating_a_link_via_the_api_requires_auth(self):
        response = self.api.post("/api/report-share-links/", {
            "period_start": "2026-06-01", "period_end": "2026-06-30",
        })
        self.assertEqual(response.status_code, 401)

    def test_created_link_is_viewable_without_auth_and_matches_the_dashboard_report(self):
        self.api.force_authenticate(user=self.user)
        create_response = self.api.post("/api/report-share-links/", {
            "period_start": "2026-06-01", "period_end": "2026-06-30", "label": "For my CA",
        })
        self.assertEqual(create_response.status_code, 201)
        token = create_response.data["token"]

        public_client = APIClient()
        view_response = public_client.get(f"/api/shared/report/{token}/")
        self.assertEqual(view_response.status_code, 200)
        self.assertEqual(view_response.data["label"], "For my CA")
        self.assertEqual(view_response.data["report"]["total_income"], "10000.00")
        self.assertEqual(view_response.data["gstr1_summary"]["b2b_totals"]["count"], 0)

    def test_expired_link_returns_410(self):
        link = ReportShareLink.objects.create(
            user=self.user, period_start=date(2026, 6, 1), period_end=date(2026, 6, 30),
            expires_at=timezone.now() - timedelta(days=1),
        )
        public_client = APIClient()
        response = public_client.get(f"/api/shared/report/{link.token}/")
        self.assertEqual(response.status_code, 410)

    def test_unknown_token_returns_404(self):
        public_client = APIClient()
        response = public_client.get("/api/shared/report/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_a_user_only_sees_their_own_share_links(self):
        other_user = User.objects.create_user(email="other@example.com", password="testpass123")
        ReportShareLink.objects.create(
            user=other_user, period_start=date(2026, 6, 1), period_end=date(2026, 6, 30),
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.api.force_authenticate(user=self.user)
        response = self.api.get("/api/report-share-links/")
        self.assertEqual(response.data, [])
