from django.conf import settings
from django.db import models

# Free tier ships with no plan/pricing model in the database at all - it's
# just "no active Subscription row", enforced entirely in services/limits.py.
# Only the paid tier needs a real record, created once a Razorpay
# subscription actually exists.
FREE_TIER_MONTHLY_INVOICE_LIMIT = 5


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past due"
    CANCELLED = "cancelled", "Cancelled"


class Subscription(models.Model):
    """A user's Pro-plan subscription state, mirrored from Razorpay Subscriptions."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    razorpay_subscription_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=12, choices=SubscriptionStatus.choices, default=SubscriptionStatus.CANCELLED)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_pro(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE

    def __str__(self):
        return f"Subscription({self.user.email}, {self.status})"
