from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import BusinessProfile, User
from clients.models import Client
from expenses.models import Expense, ExpenseCategory
from invoicing.models import Invoice, InvoiceStatus, TaxType
from reports.services.insights import (
    expense_breakdown_by_category, monthly_revenue_trend, top_clients_by_revenue,
)


class InsightsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_a = Client.objects.create(user=self.user, name="Client A", country="India", state="Maharashtra")
        self.client_b = Client.objects.create(user=self.user, name="Client B", country="India", state="Maharashtra")
        self.category = ExpenseCategory.objects.get(user=self.user, name="Software & Subscriptions")

    def _paid_invoice(self, client_obj, subtotal, paid_at):
        return Invoice.objects.create(
            user=self.user, client=client_obj,
            client_name_snapshot=client_obj.name, client_country_snapshot="India",
            invoice_number=f"TEST-{Invoice.objects.count() + 1}",
            issue_date=paid_at.date(), due_date=paid_at.date(), tax_type=TaxType.CGST_SGST,
            subtotal=subtotal, total_amount=subtotal, status=InvoiceStatus.PAID, paid_at=paid_at,
        )

    def test_monthly_revenue_trend_buckets_by_paid_month(self):
        self._paid_invoice(self.client_a, Decimal("10000"), timezone.make_aware(timezone.datetime(2026, 6, 15)))
        Expense.objects.create(
            user=self.user, category=self.category, vendor_name="AWS",
            amount=Decimal("500"), expense_date=date(2026, 6, 10),
        )
        trend = monthly_revenue_trend(self.user, months=3)
        june = next(row for row in trend if row["month"] == "2026-06")
        self.assertEqual(june["total_income"], Decimal("10000.00"))
        self.assertEqual(june["total_expense"], Decimal("500.00"))
        self.assertEqual(len(trend), 3)

    def test_expense_breakdown_groups_by_category(self):
        Expense.objects.create(
            user=self.user, category=self.category, vendor_name="AWS",
            amount=Decimal("300"), expense_date=date(2026, 6, 10),
        )
        Expense.objects.create(
            user=self.user, category=self.category, vendor_name="GCP",
            amount=Decimal("200"), expense_date=date(2026, 6, 12),
        )
        breakdown = expense_breakdown_by_category(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]["category"], "Software & Subscriptions")
        self.assertEqual(breakdown[0]["total"], Decimal("500.00"))

    def test_top_clients_ranks_by_revenue_descending(self):
        self._paid_invoice(self.client_a, Decimal("5000"), timezone.make_aware(timezone.datetime(2026, 6, 15)))
        self._paid_invoice(self.client_b, Decimal("9000"), timezone.make_aware(timezone.datetime(2026, 6, 16)))
        top = top_clients_by_revenue(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(top[0]["client_name"], "Client B")
        self.assertEqual(top[0]["total"], Decimal("9000.00"))
        self.assertEqual(top[1]["client_name"], "Client A")


class DashboardInsightsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_endpoint_returns_all_three_sections(self):
        response = self.api.get("/api/reports/insights/", {"period_start": "2026-06-01", "period_end": "2026-06-30"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("monthly_revenue_trend", response.data)
        self.assertIn("expense_breakdown", response.data)
        self.assertIn("top_clients", response.data)
