from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    BusinessProfileView, LogoutView, MeView, PasswordResetConfirmView,
    PasswordResetRequestView, RegisterView, ThrottledTokenObtainPairView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", ThrottledTokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("business-profile/", BusinessProfileView.as_view(), name="business-profile"),
]
