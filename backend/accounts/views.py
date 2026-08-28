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

from .models import BusinessProfile, NotificationPreference
from .serializers import (
    BusinessProfileSerializer, ChangeEmailSerializer, ChangePasswordSerializer,
    DeleteAccountSerializer, LogoutSerializer, NotificationPreferenceSerializer,
    OnboardingStatusSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer,
    RegisterSerializer, UserSerializer,
)
from .services.account_deletion import delete_user_account
from .services.data_export import export_all_user_data_zip
from .services.password_reset import reset_password_with_token, send_password_reset_email


class RegisterView(generics.CreateAPIView):
    """FR-1: account signup."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """FR-1 login, rate-limited against credential-stuffing/brute-force attempts."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


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
