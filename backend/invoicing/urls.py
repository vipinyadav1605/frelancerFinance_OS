from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExchangeRateView, InvoiceViewSet, PublicInvoiceView, RazorpayWebhookView,
    RecurringInvoiceProfileViewSet,
)

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("recurring-invoices", RecurringInvoiceProfileViewSet, basename="recurring-invoice")

urlpatterns = [
    path("webhooks/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    path("invoicing/exchange-rate/", ExchangeRateView.as_view(), name="exchange-rate"),
    path("public/invoice/<str:token>/", PublicInvoiceView.as_view(), name="public-invoice"),
] + router.urls
