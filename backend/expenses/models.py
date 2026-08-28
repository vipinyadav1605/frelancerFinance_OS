from django.conf import settings
from django.db import models


class ExpenseCategory(models.Model):
    """A per-user expense category. Defaults are seeded on signup (see signals.py)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expense_categories")
    name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        unique_together = ["user", "name"]

    def __str__(self):
        return self.name


class ExpenseSource(models.TextChoices):
    MANUAL = "manual", "Manual entry"
    CSV_IMPORT = "csv_import", "CSV import"


class BankStatementImportStatus(models.TextChoices):
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class BankStatementImport(models.Model):
    """One CSV upload event; expenses created from it link back here (FR: Phase 2)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bank_statement_imports")
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=BankStatementImportStatus.choices, default=BankStatementImportStatus.PROCESSING)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self):
        return f"{self.file_name} ({self.status})"


class Expense(models.Model):
    """A single business expense, entered manually or imported from a bank/UPI CSV."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    vendor_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="GST you paid on this expense, if any - used for the input tax credit estimate in Reports.",
    )
    expense_date = models.DateField()
    source = models.CharField(max_length=12, choices=ExpenseSource.choices, default=ExpenseSource.MANUAL)
    bank_statement_import = models.ForeignKey(
        BankStatementImport, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    receipt_file = models.FileField(upload_to="receipts/%Y/%m/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-id"]
        indexes = [
            models.Index(fields=["user", "expense_date"]),
        ]

    def __str__(self):
        return f"{self.vendor_name} - {self.amount} ({self.expense_date})"
