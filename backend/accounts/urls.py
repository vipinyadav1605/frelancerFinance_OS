from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    BusinessProfileView, ChangeEmailView, ChangePasswordView, DataExportView,
    DeleteAccountView, LogoutView, MeView, NotificationPreferenceView,
    OnboardingStatusView, PasswordResetConfirmView, PasswordResetRequestView,
    RegisterView, ThrottledTokenObtainPairView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", ThrottledTokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("change-email/", ChangeEmailView.as_view(), name="auth-change-email"),
    path("delete-account/", DeleteAccountView.as_view(), name="auth-delete-account"),
    path("notification-preference/", NotificationPreferenceView.as_view(), name="notification-preference"),
    path("onboarding-status/", OnboardingStatusView.as_view(), name="onboarding-status"),
    path("data-export/", DataExportView.as_view(), name="data-export"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("business-profile/", BusinessProfileView.as_view(), name="business-profile"),
]
