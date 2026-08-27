from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from expenses.models import ExpenseCategory
from expenses.serializers import MAX_UPLOAD_SIZE_BYTES


class ReceiptUploadValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.category = ExpenseCategory.objects.get(user=self.user, name="Software & Subscriptions")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _post_expense(self, receipt_file):
        return self.api.post("/api/expenses/", {
            "category": self.category.id, "vendor_name": "AWS", "amount": "1000",
            "gst_paid": "0", "expense_date": "2026-06-10", "receipt_file": receipt_file,
        }, format="multipart")

    def test_valid_pdf_receipt_is_accepted(self):
        receipt = SimpleUploadedFile("receipt.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        response = self._post_expense(receipt)
        self.assertEqual(response.status_code, 201)

    def test_disallowed_content_type_is_rejected(self):
        receipt = SimpleUploadedFile("receipt.exe", b"MZ fake exe", content_type="application/x-msdownload")
        response = self._post_expense(receipt)
        self.assertEqual(response.status_code, 400)
        self.assertIn("receipt_file", response.data)

    def test_oversized_receipt_is_rejected(self):
        receipt = SimpleUploadedFile(
            "receipt.pdf", b"x" * (MAX_UPLOAD_SIZE_BYTES + 1), content_type="application/pdf"
        )
        response = self._post_expense(receipt)
        self.assertEqual(response.status_code, 400)
        self.assertIn("receipt_file", response.data)


class CsvImportValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_non_csv_extension_is_rejected(self):
        upload = SimpleUploadedFile("statement.txt", b"date,desc,amount\n", content_type="text/plain")
        response = self.api.post("/api/expenses/import-csv/", {
            "file": upload, "date_column": "date", "description_column": "desc", "amount_column": "amount",
        }, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)

    def test_oversized_csv_is_rejected(self):
        upload = SimpleUploadedFile(
            "statement.csv", b"x" * (MAX_UPLOAD_SIZE_BYTES + 1), content_type="text/csv"
        )
        response = self.api.post("/api/expenses/import-csv/", {
            "file": upload, "date_column": "date", "description_column": "desc", "amount_column": "amount",
        }, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)
