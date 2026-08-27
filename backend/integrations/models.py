import hashlib
import secrets

from django.conf import settings
from django.db import models

API_KEY_PREFIX = "ffos"


def _generate_api_key():
    """Returns (full_key_to_show_once, prefix_for_display, sha256_hash_to_store)."""
    secret = secrets.token_urlsafe(32)
    full_key = f"{API_KEY_PREFIX}_{secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    display_prefix = full_key[:12]
    return full_key, display_prefix, key_hash


class ApiKey(models.Model):
    """
    Phase 5: personal API keys for scripting/automation (e.g. a personal
    Zapier/n8n flow). Only the SHA-256 hash is stored - the real key is shown
    to the user exactly once, at creation time, like GitHub personal tokens.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=64, unique=True, editable=False)
    display_prefix = models.CharField(max_length=16, editable=False)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.display_prefix}...)"

    @property
    def is_active(self):
        return self.revoked_at is None


class WebhookEvent(models.TextChoices):
    INVOICE_PAID = "invoice.paid", "Invoice paid"
    INVOICE_OVERDUE = "invoice.overdue", "Invoice overdue"
    EXPENSE_CREATED = "expense.created", "Expense created"


class WebhookSubscription(models.Model):
    """Phase 5: outgoing webhooks for third-party integrations."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="webhook_subscriptions")
    url = models.URLField()
    event = models.CharField(max_length=30, choices=WebhookEvent.choices)
    secret = models.CharField(max_length=64, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} -> {self.url}"


class WebhookDelivery(models.Model):
    """Delivery log, so a user can debug why an integration isn't firing."""

    subscription = models.ForeignKey(WebhookSubscription, on_delete=models.CASCADE, related_name="deliveries")
    event = models.CharField(max_length=30)
    payload = models.JSONField()
    status_code = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
