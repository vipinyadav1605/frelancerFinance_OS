import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class TaxEstimate(models.Model):
    """
    A cached profit & loss / GST snapshot for one period, per Document 2's
    ER diagram. Recomputed (via update_or_create) each time the period is
    viewed, so it doubles as a lightweight history of past estimates.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tax_estimates")
    period_start = models.DateField()
    period_end = models.DateField()

    total_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    gst_output_tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_input_tax_credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estimated_gst_liability = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Income tax (44ADA) is inherently an annual figure, not a per-period one,
    # so it's always computed for the financial year containing period_end -
    # these two fields make that explicit rather than implying it covers
    # just period_start..period_end.
    financial_year_start = models.DateField()
    financial_year_end = models.DateField()
    financial_year_gross_receipts = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estimated_income_tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "period_start", "period_end"]
        ordering = ["-period_start"]

    def __str__(self):
        return f"TaxEstimate({self.user_id}, {self.period_start}..{self.period_end})"


def _generate_share_token():
    return secrets.token_urlsafe(24)


class ReportShareLink(models.Model):
    """
    Phase 5 "team access": rather than building full multi-user accounts with
    roles (overkill for a single freelancer whose only real "team" need is
    occasionally giving their CA a look), this is a scoped, expiring,
    read-only link to one P&L/GST/GSTR-1 snapshot. No login required to view
    it - anyone with the link (and before it expires) can see that one report.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="report_share_links")
    token = models.CharField(max_length=64, unique=True, default=_generate_share_token, editable=False)
    period_start = models.DateField()
    period_end = models.DateField()
    label = models.CharField(max_length=100, blank=True, help_text="e.g. \"For Ramesh, my CA\"")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Share link for {self.user_id} ({self.period_start}..{self.period_end})"
