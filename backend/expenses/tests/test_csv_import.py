import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import User
from expenses.models import BankStatementImportStatus, Expense, ExpenseCategory
from expenses.services.csv_import import _parse_amount, _parse_date, import_bank_statement_csv


class ParseHelpersTests(TestCase):
    def test_parse_date_handles_common_formats(self):
        self.assertEqual(str(_parse_date("2026-08-23")), "2026-08-23")
        self.assertEqual(str(_parse_date("23/08/2026")), "2026-08-23")
        self.assertEqual(str(_parse_date("23-08-2026")), "2026-08-23")

    def test_parse_date_returns_none_for_garbage(self):
        self.assertIsNone(_parse_date("not a date"))

    def test_parse_amount_strips_currency_and_commas(self):
        self.assertEqual(_parse_amount("₹1,234.50"), Decimal("1234.50"))
        self.assertEqual(_parse_amount("1234.50"), Decimal("1234.50"))

    def test_parse_amount_handles_parens_as_negative_but_returns_abs(self):
        self.assertEqual(_parse_amount("(500.00)"), Decimal("500.00"))

    def test_parse_amount_returns_none_for_zero_or_blank(self):
        self.assertIsNone(_parse_amount("0"))
        self.assertIsNone(_parse_amount(""))


class ImportBankStatementCsvTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        # Signal seeds default categories on user creation.

    def _csv_file(self, content: str, name="statement.csv"):
        return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")

    def test_imports_valid_rows_and_autocategorizes(self):
        csv_content = (
            "Date,Narration,Withdrawal\n"
            "23/08/2026,AWS Cloud Services,1500.00\n"
            "24/08/2026,Uber Ride to airport,450.00\n"
            "25/08/2026,Random Unknown Vendor XYZ,200.00\n"
        )
        result = import_bank_statement_csv(
            user=self.user, uploaded_file=self._csv_file(csv_content),
            date_column="Date", description_column="Narration", amount_column="Withdrawal",
        )
        self.assertEqual(result.status, BankStatementImportStatus.COMPLETED)
        self.assertEqual(result.imported_count, 3)
        self.assertEqual(result.skipped_count, 0)

        aws_expense = Expense.objects.get(vendor_name__icontains="AWS")
        self.assertEqual(aws_expense.category.name, "Software & Subscriptions")

        uber_expense = Expense.objects.get(vendor_name__icontains="Uber")
        self.assertEqual(uber_expense.category.name, "Travel")

        unknown_expense = Expense.objects.get(vendor_name__icontains="Unknown")
        self.assertEqual(unknown_expense.category.name, "Other")

    def test_skips_rows_with_unparseable_amount_or_date(self):
        csv_content = (
            "Date,Narration,Withdrawal\n"
            "23/08/2026,Valid Row,100.00\n"
            "not-a-date,Bad Date Row,100.00\n"
            "24/08/2026,Bad Amount Row,not-a-number\n"
            "25/08/2026,Zero Amount Row,0\n"
        )
        result = import_bank_statement_csv(
            user=self.user, uploaded_file=self._csv_file(csv_content),
            date_column="Date", description_column="Narration", amount_column="Withdrawal",
        )
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.skipped_count, 3)

    def test_fails_cleanly_when_mapped_column_missing(self):
        csv_content = "Date,Narration,Withdrawal\n23/08/2026,Test,100.00\n"
        result = import_bank_statement_csv(
            user=self.user, uploaded_file=self._csv_file(csv_content),
            date_column="Date", description_column="Narration", amount_column="DoesNotExist",
        )
        self.assertEqual(result.status, BankStatementImportStatus.FAILED)
        self.assertIn("missing", result.error_message.lower())

    def test_default_categories_seeded_on_user_creation(self):
        categories = list(ExpenseCategory.objects.filter(user=self.user).values_list("name", flat=True))
        self.assertIn("Software & Subscriptions", categories)
        self.assertIn("Other", categories)
        self.assertEqual(len(categories), 8)
