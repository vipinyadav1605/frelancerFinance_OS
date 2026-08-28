import secrets

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .constants import INDIAN_STATE_CHOICES
from .managers import UserManager


def _generate_referral_code():
    return secrets.token_urlsafe(6)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user, authenticated by email (FR-1)."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    # Growth loop: every user gets a shareable `/register?ref=<code>` link.
    # Reward for a successful referral is granted in
    # invoicing.views._handle_subscription_event when the referred user's
    # subscription first goes active - see billing/services/referrals.py.
    referral_code = models.CharField(max_length=16, unique=True, default=_generate_referral_code, editable=False)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals",
    )

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
    email_signoff = models.CharField(
        max_length=255, blank=True,
        help_text="Replaces the default \"Thanks, {business_name}\" sign-off on invoice/reminder emails.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} ({self.user.email})"


class NotificationPreference(models.Model):
    """Per-user toggles for EMAILED notifications (in-app notifications are never gated by this)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preference")
    payment_confirmation_emails = models.BooleanField(default=True)
    webhook_failure_emails = models.BooleanField(default=True)

    def __str__(self):
        return f"NotificationPreference({self.user.email})"


class TwoFactorAuth(models.Model):
    """
    TOTP-based 2FA. `secret` is generated at /2fa/setup/ time but `is_enabled`
    stays False until the user proves they've actually added it to an
    authenticator app by submitting one valid code to /2fa/enable/ - this
    avoids a user getting locked out from a setup that never actually landed
    in their app (e.g. they closed the tab before scanning the QR code).
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="two_factor_auth")
    secret = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TwoFactorAuth({self.user.email}, enabled={self.is_enabled})"
