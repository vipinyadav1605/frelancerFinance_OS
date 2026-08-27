from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from clients.models import Client
from invoicing.models import TaxType
from invoicing.services.tax import calculate_invoice_totals, determine_tax_type


class DetermineTaxTypeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")

    def test_same_state_domestic_client_is_cgst_sgst(self):
        client = Client.objects.create(
            user=self.user, name="Same State Co", country="India", state="Maharashtra",
        )
        self.assertEqual(determine_tax_type("Maharashtra", client), TaxType.CGST_SGST)

    def test_other_state_domestic_client_is_igst(self):
        client = Client.objects.create(
            user=self.user, name="Other State Co", country="India", state="Karnataka",
        )
        self.assertEqual(determine_tax_type("Maharashtra", client), TaxType.IGST)

    def test_international_client_is_export_zero_rated(self):
        client = Client.objects.create(
            user=self.user, name="Acme Inc", country="United States",
        )
        self.assertTrue(client.is_international)
        self.assertEqual(determine_tax_type("Maharashtra", client), TaxType.EXPORT_ZERO_RATED)


class CalculateInvoiceTotalsTests(TestCase):
    def test_cgst_sgst_splits_tax_evenly(self):
        items = [{"quantity": Decimal("1"), "unit_price": Decimal("1000"), "tax_rate_percent": Decimal("18")}]
        totals = calculate_invoice_totals(items, TaxType.CGST_SGST)
        self.assertEqual(totals["subtotal"], Decimal("1000.00"))
        self.assertEqual(totals["cgst_amount"], Decimal("90.00"))
        self.assertEqual(totals["sgst_amount"], Decimal("90.00"))
        self.assertEqual(totals["igst_amount"], Decimal("0.00"))
        self.assertEqual(totals["total_amount"], Decimal("1180.00"))

    def test_igst_applies_full_rate(self):
        items = [{"quantity": Decimal("2"), "unit_price": Decimal("500"), "tax_rate_percent": Decimal("18")}]
        totals = calculate_invoice_totals(items, TaxType.IGST)
        self.assertEqual(totals["subtotal"], Decimal("1000.00"))
        self.assertEqual(totals["igst_amount"], Decimal("180.00"))
        self.assertEqual(totals["cgst_amount"], Decimal("0.00"))
        self.assertEqual(totals["total_amount"], Decimal("1180.00"))

    def test_export_is_zero_rated_regardless_of_item_tax_rate(self):
        items = [{"quantity": Decimal("1"), "unit_price": Decimal("500"), "tax_rate_percent": Decimal("18")}]
        totals = calculate_invoice_totals(items, TaxType.EXPORT_ZERO_RATED)
        self.assertEqual(totals["cgst_amount"], Decimal("0.00"))
        self.assertEqual(totals["sgst_amount"], Decimal("0.00"))
        self.assertEqual(totals["igst_amount"], Decimal("0.00"))
        self.assertEqual(totals["total_amount"], Decimal("500.00"))

    def test_multiple_line_items_sum_correctly(self):
        items = [
            {"quantity": Decimal("1"), "unit_price": Decimal("1000"), "tax_rate_percent": Decimal("18")},
            {"quantity": Decimal("3"), "unit_price": Decimal("200"), "tax_rate_percent": Decimal("18")},
        ]
        totals = calculate_invoice_totals(items, TaxType.CGST_SGST)
        self.assertEqual(totals["subtotal"], Decimal("1600.00"))
        self.assertEqual(totals["total_amount"], Decimal("1888.00"))
