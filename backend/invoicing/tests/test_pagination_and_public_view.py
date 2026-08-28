from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import BusinessProfile, User
from clients.models import Client
from invoicing.models import Invoice, InvoiceStatus, TaxType


class InvoiceListPaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        for i in range(30):
            Invoice.objects.create(
                user=self.user, client=self.client_obj,
                client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
                invoice_number=f"TEST-{i}", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
                tax_type=TaxType.CGST_SGST, subtotal=Decimal("1000"), total_amount=Decimal("1000"),
                status=InvoiceStatus.DRAFT,
            )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_list_is_paginated_with_default_page_size(self):
        response = self.api.get("/api/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 30)
        self.assertEqual(len(response.data["results"]), 25)
        self.assertIsNotNone(response.data["next"])

    def test_second_page_returns_remaining_items(self):
        response = self.api.get("/api/invoices/", {"page": 2})
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNone(response.data["next"])

    def test_page_size_can_be_overridden_up_to_max(self):
        response = self.api.get("/api/invoices/", {"page_size": 5})
        self.assertEqual(len(response.data["results"]), 5)


class PublicInvoiceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra", gstin="27AAAAA0000A1Z5")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        self.invoice = Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("10000"), cgst_amount=Decimal("900"),
            sgst_amount=Decimal("900"), total_amount=Decimal("11800"), status=InvoiceStatus.SENT,
        )
        self.api = APIClient()

    def test_public_view_works_without_auth(self):
        response = self.api.get(f"/api/public/invoice/{self.invoice.public_view_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["invoice_number"], "TEST-1")
        self.assertEqual(response.data["business_name"], "Riya Design")
        self.assertEqual(response.data["total_amount"], "11800.00")

    def test_public_view_does_not_expose_internal_id_or_client_fk(self):
        response = self.api.get(f"/api/public/invoice/{self.invoice.public_view_token}/")
        self.assertNotIn("id", response.data)
        self.assertNotIn("client", response.data)

    def test_unknown_token_returns_404(self):
        response = self.api.get("/api/public/invoice/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_each_invoice_gets_a_unique_token(self):
        other = Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-2", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("500"), total_amount=Decimal("500"),
        )
        self.assertNotEqual(self.invoice.public_view_token, other.public_view_token)
