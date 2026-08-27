from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import BusinessProfile, User
from clients.models import Client
from expenses.models import Expense, ExpenseCategory
from invoicing.models import Invoice, InvoiceStatus, TaxType
from reports.services.profit_loss import compute_profit_loss


class ComputeProfitLossTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(
            user=self.user, name="Mumbai Co", country="India", state="Maharashtra",
        )
        self.software_category = ExpenseCategory.objects.get(user=self.user, name="Software & Subscriptions")

    def _make_paid_invoice(self, subtotal, cgst, sgst, paid_at):
        invoice = Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number=f"TEST-{Invoice.objects.count() + 1}",
            issue_date=paid_at.date(), due_date=paid_at.date(),
            tax_type=TaxType.CGST_SGST,
            subtotal=subtotal, cgst_amount=cgst, sgst_amount=sgst,
            total_amount=subtotal + cgst + sgst,
            status=InvoiceStatus.PAID, paid_at=paid_at,
        )
        return invoice

    def test_income_uses_subtotal_not_tax_inclusive_total(self):
        self._make_paid_invoice(
            Decimal("10000"), Decimal("900"), Decimal("900"),
            timezone.make_aware(timezone.datetime(2026, 6, 15)),
        )
        estimate = compute_profit_loss(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(estimate.total_income, Decimal("10000.00"))
        self.assertEqual(estimate.gst_output_tax, Decimal("1800.00"))

    def test_expenses_reduce_net_profit_and_gst_input_credit_reduces_liability(self):
        self._make_paid_invoice(
            Decimal("10000"), Decimal("900"), Decimal("900"),
            timezone.make_aware(timezone.datetime(2026, 6, 15)),
        )
        Expense.objects.create(
            user=self.user, category=self.software_category, vendor_name="AWS",
            amount=Decimal("1000"), gst_paid=Decimal("180"), expense_date=date(2026, 6, 10),
        )
        estimate = compute_profit_loss(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(estimate.total_expense, Decimal("1000.00"))
        self.assertEqual(estimate.net_profit, Decimal("9000.00"))
        self.assertEqual(estimate.gst_input_tax_credit, Decimal("180.00"))
        self.assertEqual(estimate.estimated_gst_liability, Decimal("1620.00"))  # 1800 - 180

    def test_invoices_outside_period_are_excluded(self):
        self._make_paid_invoice(
            Decimal("10000"), Decimal("900"), Decimal("900"),
            timezone.make_aware(timezone.datetime(2026, 5, 15)),
        )
        estimate = compute_profit_loss(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(estimate.total_income, Decimal("0.00"))

    def test_financial_year_gross_receipts_independent_of_selected_period(self):
        self._make_paid_invoice(
            Decimal("500000"), Decimal("0"), Decimal("0"),
            timezone.make_aware(timezone.datetime(2026, 5, 1)),
        )
        # Selected period is June, but the FY (Apr 2026 - Mar 2027) should still pick up the May invoice.
        estimate = compute_profit_loss(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(estimate.financial_year_start, date(2026, 4, 1))
        self.assertEqual(estimate.financial_year_end, date(2027, 3, 31))
        self.assertEqual(estimate.financial_year_gross_receipts, Decimal("500000.00"))
