from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from clients.models import Client
from invoicing.models import Invoice, TaxType


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.other_user = User.objects.create_user(email="other@example.com", password="testpass123")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        self.invoice = Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot="Mumbai Co", client_country_snapshot="India",
            invoice_number="INV-0042", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("1000"), total_amount=Decimal("1000"),
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_finds_invoice_by_number(self):
        response = self.api.get("/api/search/", {"q": "0042"})
        self.assertEqual(response.status_code, 200)
        labels = [r["label"] for r in response.data["results"]]
        self.assertTrue(any("INV-0042" in label for label in labels))

    def test_finds_invoice_by_client_name(self):
        response = self.api.get("/api/search/", {"q": "Mumbai"})
        types = {r["type"] for r in response.data["results"]}
        self.assertIn("invoice", types)
        self.assertIn("client", types)

    def test_query_too_short_returns_empty(self):
        response = self.api.get("/api/search/", {"q": "M"})
        self.assertEqual(response.data["results"], [])

    def test_does_not_return_another_users_data(self):
        Client.objects.create(user=self.other_user, name="Mumbai Secret Co", country="India", state="Maharashtra")
        response = self.api.get("/api/search/", {"q": "Mumbai"})
        labels = [r["label"] for r in response.data["results"]]
        self.assertFalse(any("Secret" in label for label in labels))
