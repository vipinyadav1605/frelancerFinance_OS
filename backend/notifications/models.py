from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    INVOICE_OVERDUE = "invoice_overdue", "Invoice overdue"
    INVOICE_PAID = "invoice_paid", "Invoice paid"
    RECURRING_INVOICE_GENERATED = "recurring_invoice_generated", "Recurring invoice generated"
    WEBHOOK_FAILED = "webhook_failed", "Webhook delivery failed"
    REFERRAL_REWARD_GRANTED = "referral_reward_granted", "Referral reward granted"


class Notification(models.Model):
    """
    In-app notification bell + activity history, combined into one model
    rather than building two parallel systems: every notification IS an
    activity-log entry (read or not), and the bell just filters/highlights
    the unread ones. See Settings > Notifications for the emailed subset.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    message = models.CharField(max_length=255)
    link_path = models.CharField(max_length=255, blank=True, help_text="Frontend route to link to, e.g. /invoices/12")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type}: {self.message}"
