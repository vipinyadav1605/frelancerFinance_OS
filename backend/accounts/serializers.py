from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import BusinessProfile, NotificationPreference, User
from .services.two_factor import verify_code
from .validators import validate_gstin_format, validate_pan_format


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    # The REFERRER's own referral_code, not this new user's - a silently
    # ignored unknown/blank code just means no referrer, never a validation error.
    referred_by_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "email", "name", "password", "referred_by_code"]

    def create(self, validated_data):
        referred_by_code = validated_data.pop("referred_by_code", "").strip()
        referred_by = User.objects.filter(referral_code=referred_by_code).first() if referred_by_code else None
        return User.objects.create_user(referred_by=referred_by, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    has_business_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "has_business_profile"]

    def get_has_business_profile(self, obj):
        return BusinessProfile.objects.filter(user=obj).exists()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            "id", "business_name", "pan", "gstin", "is_gst_registered",
            "address", "state", "invoice_prefix", "lut_reference", "email_signoff",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_gstin(self, value):
        return validate_gstin_format(value)

    def validate_pan(self, value):
        return validate_pan_format(value)


class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    current_password = serializers.CharField(write_only=True)

    def validate_new_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.context["request"].user.pk).exists():
            raise serializers.ValidationError("Another account already uses this email.")
        return value

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class DeleteAccountSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["payment_confirmation_emails", "webhook_failure_emails"]


class OnboardingStatusSerializer(serializers.Serializer):
    has_business_profile = serializers.BooleanField()
    has_client = serializers.BooleanField()
    has_invoice = serializers.BooleanField()
    has_sent_invoice = serializers.BooleanField()


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class MicrosoftLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class GitHubLoginSerializer(serializers.Serializer):
    code = serializers.CharField()


class TwoFactorConfirmSetupSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class TwoFactorDisableSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class TwoFactorTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the standard email+password login to also require a TOTP code
    when the user has 2FA enabled. Single request, not a two-step token
    exchange: the frontend submits email+password first; if the response
    comes back with `two_factor_required: true` it re-submits the same
    request with `otp_code` filled in (see accounts/views.py's
    ThrottledTokenObtainPairView docstring for why this shape was chosen).
    """

    otp_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        otp_code = attrs.pop("otp_code", "")
        data = super().validate(attrs)

        tfa = getattr(self.user, "two_factor_auth", None)
        if tfa is not None and tfa.is_enabled:
            if not otp_code:
                raise serializers.ValidationError({
                    "detail": "Two-factor authentication code required.",
                    "two_factor_required": True,
                })
            if not verify_code(self.user, otp_code):
                raise serializers.ValidationError({"otp_code": "Invalid or expired code."})
        return data
