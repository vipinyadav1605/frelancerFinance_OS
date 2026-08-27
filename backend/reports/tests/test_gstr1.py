from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import BusinessProfile, User
from clients.models import Client
from invoicing.models import Invoice, InvoiceStatus, TaxType
from reports.services.gstr1 import compute_gstr1_prefill


class ComputeGstr1PrefillTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")

    def _make_invoice(self, client_obj, tax_type, issue_date, status=InvoiceStatus.SENT, **overrides):
        defaults = dict(
            user=self.user, client=client_obj,
            client_name_snapshot=client_obj.name, client_country_snapshot=client_obj.country,
            client_state_snapshot=client_obj.state, client_gstin_snapshot=client_obj.gstin,
            invoice_number=f"TEST-{Invoice.objects.count() + 1}",
            issue_date=issue_date, due_date=issue_date, tax_type=tax_type,
            subtotal=Decimal("10000"), total_amount=Decimal("11800"),
            cgst_amount=Decimal("900"), sgst_amount=Decimal("900"), status=status,
        )
        defaults.update(overrides)
        return Invoice.objects.create(**defaults)

    def test_registered_domestic_client_goes_to_b2b(self):
        registered = Client.objects.create(
            user=self.user, name="Regd Co", country="India", state="Maharashtra", gstin="27AAAAA0000A1Z5",
        )
        self._make_invoice(registered, TaxType.CGST_SGST, date(2026, 6, 10))
        data = compute_gstr1_prefill(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["b2b_totals"]["count"], 1)
        self.assertEqual(data["b2c_totals"]["count"], 0)
        self.assertEqual(data["b2b_totals"]["taxable_value"], Decimal("10000"))

    def test_unregistered_domestic_client_goes_to_b2c(self):
        unregistered = Client.objects.create(user=self.user, name="Small Co", country="India", state="Maharashtra")
        self._make_invoice(unregistered, TaxType.CGST_SGST, date(2026, 6, 10))
        data = compute_gstr1_prefill(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["b2c_totals"]["count"], 1)
        self.assertEqual(data["b2b_totals"]["count"], 0)

    def test_international_client_goes_to_exports(self):
        foreign = Client.objects.create(user=self.user, name="Acme Inc", country="United States")
        self._make_invoice(
            foreign, TaxType.EXPORT_ZERO_RATED, date(2026, 6, 10),
            cgst_amount=Decimal("0"), sgst_amount=Decimal("0"), total_amount=Decimal("10000"),
        )
        data = compute_gstr1_prefill(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["exports_totals"]["count"], 1)
        self.assertEqual(data["exports_totals"]["tax_amount"], Decimal("0"))

    def test_draft_invoices_are_excluded(self):
        client_obj = Client.objects.create(user=self.user, name="Regd Co", country="India", state="Maharashtra", gstin="27AAAAA0000A1Z5")
        self._make_invoice(client_obj, TaxType.CGST_SGST, date(2026, 6, 10), status=InvoiceStatus.DRAFT)
        data = compute_gstr1_prefill(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["b2b_totals"]["count"], 0)

    def test_uses_issue_date_not_paid_date_for_bucketing_period(self):
        client_obj = Client.objects.create(user=self.user, name="Regd Co", country="India", state="Maharashtra", gstin="27AAAAA0000A1Z5")
        # Issued in June, still unpaid - must still count for June's GSTR-1 (accrual basis).
        self._make_invoice(client_obj, TaxType.CGST_SGST, date(2026, 6, 28), status=InvoiceStatus.SENT)
        data = compute_gstr1_prefill(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["b2b_totals"]["count"], 1)

    def test_effective_rate_percent_is_derived_from_tax_amounts(self):
        client_obj = Client.objects.create(user=self.user, name="Regd Co", country="India", state="Maharashtra", gstin="27AAAAA0000A1Z5")
        self._make_invoice(client_obj, TaxType.CGST_SGST, date(2026, 6, 10))
        data = compute_gstr1_prefill(self.user, date(2026, 6, 1), date(2026, 6, 30))
        self.assertEqual(data["b2b"][0]["rate_percent"], Decimal("18.00"))
