from django.urls import path

from .views import BillingStatusView, CancelSubscriptionView, SubscribeView

urlpatterns = [
    path("billing/status/", BillingStatusView.as_view(), name="billing-status"),
    path("billing/subscribe/", SubscribeView.as_view(), name="billing-subscribe"),
    path("billing/cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
]
