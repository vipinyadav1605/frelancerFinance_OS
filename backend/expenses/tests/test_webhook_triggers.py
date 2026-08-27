from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from expenses.models import ExpenseCategory


class ExpenseCreatedWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.category = ExpenseCategory.objects.get(user=self.user, name="Software & Subscriptions")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    @patch("expenses.views.send_webhook_event")
    def test_manual_expense_creation_fires_expense_created_webhook(self, mock_send):
        response = self.api.post("/api/expenses/", {
            "category": self.category.id, "vendor_name": "AWS", "amount": "1000",
            "gst_paid": "180", "expense_date": "2026-06-10",
        })
        self.assertEqual(response.status_code, 201)
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertEqual(args[0], self.user)
        self.assertEqual(args[1], "expense.created")
        self.assertEqual(args[2]["vendor_name"], "AWS")
