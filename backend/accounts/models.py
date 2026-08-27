from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .constants import INDIAN_STATE_CHOICES
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user, authenticated by email (FR-1)."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class BusinessProfile(models.Model):
    """A user's business details, printed on every invoice (FR-2)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business_profile")
    business_name = models.CharField(max_length=255)
    pan = models.CharField(max_length=10, blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    is_gst_registered = models.BooleanField(default=False)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=64, choices=INDIAN_STATE_CHOICES)
    invoice_prefix = models.CharField(max_length=12, default="INV")
    next_invoice_sequence = models.PositiveIntegerField(default=1)
    lut_reference = models.CharField(
        max_length=100, blank=True,
        help_text="LUT ARN reference, required to mark export invoices as zero-rated.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} ({self.user.email})"
