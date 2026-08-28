from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import BusinessProfile, User
from clients.models import Client
from expenses.models import Expense, ExpenseCategory
from invoicing.models import Invoice, InvoiceStatus, TaxType
from reports.services.gstr3b import compute_gstr3b_summary


class ComputeGstr3bSummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.category = ExpenseCategory.objects.create(user=self.user, name="Software")

    def _make_invoice(self, client_obj, tax_type, issue_date, **overrides):
        defaults = dict(
            user=self.user, client=client_obj,
            client_name_snapshot=client_obj.name, client_country_snapshot=client_obj.country,
            client_state_snapshot=client_obj.state, client_gstin_snapshot=client_obj.gstin,
            invoice_number=f"TEST-{Invoice.objects.count() + 1}",
            issue_date=issue_date, due_date=issue_date, tax_type=tax_type,
            subtotal=Decimal("10000"), total_amount=Decimal("11800"),
            cgst_amount=Decimal("900"), sgst_amount=Decimal("900"), status=InvoiceStatus.SENT,
        )
        defaults.update(overrides)
        return Invoice.objects.create(**defaults)

    def test_domestic_invoices_contribute_to_outward_taxable_supplies(self):
        registered = Client.objects.create(
            user=self.user, name="Regd Co", country="India", state="Maharashtra", gstin="27AAAAA0000A1Z5",
        )
        self._make_invoice(registered, TaxType.CGST_SGST, date(2026, 6, 10))
        data = compute_gstr3b_summary(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["outward_taxable_supplies"]["taxable_value"], Decimal("10000"))
        self.assertEqual(data["outward_taxable_supplies"]["central_tax"], Decimal("900"))
        self.assertEqual(data["outward_taxable_supplies"]["state_tax"], Decimal("900"))

    def test_export_invoices_go_to_zero_rated_bucket_not_taxable(self):
        foreign = Client.objects.create(user=self.user, name="Acme Inc", country="United States")
        self._make_invoice(
            foreign, TaxType.EXPORT_ZERO_RATED, date(2026, 6, 10),
            cgst_amount=Decimal("0"), sgst_amount=Decimal("0"), total_amount=Decimal("10000"),
        )
        data = compute_gstr3b_summary(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["outward_taxable_supplies"]["taxable_value"], Decimal("0"))
        self.assertEqual(data["outward_zero_rated_supplies"]["taxable_value"], Decimal("10000"))

    def test_eligible_itc_comes_from_expense_gst_paid_in_period(self):
        Expense.objects.create(
            user=self.user, category=self.category, vendor_name="Adobe",
            amount=Decimal("2000"), gst_paid=Decimal("360"), expense_date=date(2026, 6, 15),
        )
        data = compute_gstr3b_summary(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["eligible_itc"], Decimal("360"))

    def test_net_tax_payable_nets_output_tax_against_itc(self):
        registered = Client.objects.create(
            user=self.user, name="Regd Co", country="India", state="Maharashtra", gstin="27AAAAA0000A1Z5",
        )
        self._make_invoice(registered, TaxType.CGST_SGST, date(2026, 6, 10))
        Expense.objects.create(
            user=self.user, category=self.category, vendor_name="Adobe",
            amount=Decimal("2000"), gst_paid=Decimal("500"), expense_date=date(2026, 6, 15),
        )
        data = compute_gstr3b_summary(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["net_tax_payable"], Decimal("1300"))
        self.assertEqual(data["itc_carried_forward"], Decimal("0"))

    def test_itc_exceeding_output_tax_carries_forward_instead_of_going_negative(self):
        Expense.objects.create(
            user=self.user, category=self.category, vendor_name="Adobe",
            amount=Decimal("20000"), gst_paid=Decimal("3600"), expense_date=date(2026, 6, 15),
        )
        data = compute_gstr3b_summary(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["net_tax_payable"], Decimal("0"))
        self.assertEqual(data["itc_carried_forward"], Decimal("3600"))
