from django.conf import settings
from django.db import models

from accounts.constants import INDIAN_STATE_CHOICES


class Client(models.Model):
    """A freelancer's client, billed via invoices (FR-3)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clients")
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    billing_address = models.TextField(blank=True)
    country = models.CharField(max_length=100, default="India")
    state = models.CharField(
        max_length=64, choices=INDIAN_STATE_CHOICES, blank=True,
        help_text="Required for domestic clients, to determine CGST+SGST vs IGST.",
    )
    gstin = models.CharField(max_length=15, blank=True)
    is_international = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.is_international = self.country.strip().lower() != "india"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
