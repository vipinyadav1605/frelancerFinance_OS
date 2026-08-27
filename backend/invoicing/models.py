from django.conf import settings
from django.db import models

from clients.models import Client


class TaxType(models.TextChoices):
    CGST_SGST = "CGST_SGST", "CGST + SGST (same state)"
    IGST = "IGST", "IGST (other state)"
    EXPORT_ZERO_RATED = "EXPORT_ZERO_RATED", "Export of services (zero-rated)"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"


class Currency(models.TextChoices):
    INR = "INR", "Indian Rupee"
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "British Pound"


class Invoice(models.Model):
    """A GST-compliant invoice (FR-4, FR-5, FR-6)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="invoices")

    # Snapshot of client details at invoice creation time (FR-3, criterion 3:
    # later edits to the client record must not change past invoices).
    client_name_snapshot = models.CharField(max_length=255)
    client_email_snapshot = models.EmailField(blank=True)
    client_address_snapshot = models.TextField(blank=True)
    client_country_snapshot = models.CharField(max_length=100)
    client_state_snapshot = models.CharField(max_length=64, blank=True)
    client_gstin_snapshot = models.CharField(max_length=15, blank=True)

    invoice_number = models.CharField(max_length=32, unique=True, editable=False)
    issue_date = models.DateField()
    due_date = models.DateField()

    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.INR)
    exchange_rate_to_inr = models.DecimalField(max_digits=12, decimal_places=4, default=1)

    tax_type = models.CharField(max_length=20, choices=TaxType.choices)
    lut_reference = models.CharField(max_length=100, blank=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)

    pdf_file = models.FileField(upload_to="invoices/%Y/%m/", blank=True, null=True)
    payment_link_url = models.URLField(blank=True)
    razorpay_payment_link_id = models.CharField(max_length=64, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-id"]

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    hsn_sac_code = models.CharField(max_length=10, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, editable=False, default=0)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} x{self.quantity}"


class PaymentMethod(models.TextChoices):
    RAZORPAY = "razorpay", "Razorpay"
    MANUAL = "manual", "Manual"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CAPTURED = "captured", "Captured"
    FAILED = "failed", "Failed"


class Payment(models.Model):
    """FR-6: payment tracking, from Razorpay webhooks or manual entry."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_date = models.DateTimeField()
    method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    razorpay_payment_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.invoice.invoice_number}"


class RecurringFrequency(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"


class RecurringInvoiceProfile(models.Model):
    """A template that auto-generates a real Invoice on each due cycle (Phase 4)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_profiles")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="recurring_profiles")

    frequency = models.CharField(max_length=10, choices=RecurringFrequency.choices)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.INR)
    exchange_rate_to_inr = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    due_in_days = models.PositiveIntegerField(default=14)

    next_run_date = models.DateField()
    is_active = models.BooleanField(default=True)
    auto_send = models.BooleanField(
        default=False, help_text="If set, the generated invoice is emailed to the client automatically."
    )

    last_generated_invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_run_date"]

    def __str__(self):
        return f"Recurring invoice for {self.client.name} ({self.get_frequency_display()})"


class RecurringInvoiceItem(models.Model):
    profile = models.ForeignKey(RecurringInvoiceProfile, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    hsn_sac_code = models.CharField(max_length=10, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.description} x{self.quantity}"
