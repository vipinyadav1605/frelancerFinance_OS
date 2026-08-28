from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from clients.models import Client
from invoicing.models import Invoice, InvoiceStatus

from .models import BusinessProfile, NotificationPreference, User
from .serializers import (
    BusinessProfileSerializer, ChangeEmailSerializer, ChangePasswordSerializer,
    DeleteAccountSerializer, GoogleLoginSerializer, LogoutSerializer,
    NotificationPreferenceSerializer, OnboardingStatusSerializer, PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer, RegisterSerializer, TwoFactorConfirmSetupSerializer,
    TwoFactorDisableSerializer, TwoFactorTokenObtainPairSerializer, UserSerializer,
)
from .services import two_factor
from .services.account_deletion import delete_user_account
from .services.data_export import export_all_user_data_zip
from .services.google_auth import (
    GoogleAuthNotConfigured, InvalidGoogleToken, get_or_create_user_from_google, verify_google_id_token,
)
from .services.password_reset import reset_password_with_token, send_password_reset_email


class RegisterView(generics.CreateAPIView):
    """FR-1: account signup."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """
    FR-1 login, rate-limited against credential-stuffing/brute-force attempts.
    Also enforces 2FA when enabled (see TwoFactorTokenObtainPairSerializer):
    submit email+password; if the response has `two_factor_required: true`,
    resubmit the same request with `otp_code` added.
    """

    serializer_class = TwoFactorTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class GoogleLoginView(APIView):
    """
    Sign in (or sign up) with a Google ID token from Google Identity Services.
    Returns the same {access, refresh} shape as the normal login endpoint.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            profile = verify_google_id_token(serializer.validated_data["id_token"])
        except GoogleAuthNotConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except InvalidGoogleToken:
            return Response({"detail": "Invalid Google token."}, status=status.HTTP_401_UNAUTHORIZED)

        user = get_or_create_user_from_google(profile["email"], profile["name"])
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class LogoutView(APIView):
    """Blacklists the given refresh token so it can no longer mint new access tokens."""

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            pass  # Already invalid/expired/blacklisted - logout should still succeed either way.
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    """
    Always returns 200 regardless of whether the email is registered - the
    response must not let an attacker enumerate which emails have accounts.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_password_reset_email(serializer.validated_data["email"])
        return Response({"detail": "If that email is registered, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok = reset_password_with_token(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        if not ok:
            return Response(
                {"detail": "This reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Password has been reset."})


class MeView(APIView):
    """Current user info, used by the frontend to decide the onboarding flow."""

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class BusinessProfileView(APIView):
    """FR-2: business profile setup. One profile per user (get-or-create semantics)."""

    def get(self, request):
        profile = BusinessProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(None)
        return Response(BusinessProfileSerializer(profile).data)

    def put(self, request):
        profile = BusinessProfile.objects.filter(user=request.user).first()
        serializer = BusinessProfileSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed."})


class ChangeEmailView(APIView):
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.email = serializer.validated_data["new_email"]
        request.user.save(update_fields=["email"])
        return Response(UserSerializer(request.user).data)


class DeleteAccountView(APIView):
    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        delete_user_account(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationPreferenceView(APIView):
    def get(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(preference).data)

    def put(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(preference, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OnboardingStatusView(APIView):
    """Drives the Dashboard's first-run setup checklist."""

    def get(self, request):
        invoices = Invoice.objects.filter(user=request.user)
        data = {
            "has_business_profile": BusinessProfile.objects.filter(user=request.user).exists(),
            "has_client": Client.objects.filter(user=request.user).exists(),
            "has_invoice": invoices.exists(),
            "has_sent_invoice": invoices.exclude(status=InvoiceStatus.DRAFT).exists(),
        }
        return Response(OnboardingStatusSerializer(data).data)


class DataExportView(APIView):
    """Settings > Danger Zone: download everything as a zip of CSVs."""

    def get(self, request):
        content = export_all_user_data_zip(request.user)
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="freelancer-finance-os-export.zip"'
        return response


class ReferralStatusView(APIView):
    """Settings > Billing referral nudge: the user's own code + how many people have used it."""

    def get(self, request):
        return Response({
            "referral_code": request.user.referral_code,
            "referral_count": User.objects.filter(referred_by=request.user).count(),
        })


class TwoFactorStatusView(APIView):
    def get(self, request):
        return Response({"is_enabled": two_factor.is_enabled(request.user)})


class TwoFactorSetupView(APIView):
    """Step 1: generates a pending secret + QR code. Not enabled until /2fa/confirm/ succeeds."""

    def post(self, request):
        return Response(two_factor.start_setup(request.user))


class TwoFactorConfirmView(APIView):
    """Step 2: proves the code actually works before turning 2FA on."""

    def post(self, request):
        serializer = TwoFactorConfirmSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok = two_factor.confirm_setup(request.user, serializer.validated_data["code"])
        if not ok:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Two-factor authentication enabled."})


class TwoFactorDisableView(APIView):
    def post(self, request):
        serializer = TwoFactorDisableSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        two_factor.disable(request.user)
        return Response({"detail": "Two-factor authentication disabled."})
