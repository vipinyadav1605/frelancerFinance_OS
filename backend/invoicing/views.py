import json
import logging

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from billing.models import Subscription, SubscriptionStatus
from billing.services.limits import can_create_invoice
from billing.services.referrals import grant_referral_reward
from config.pagination import StandardResultsPagination
from integrations.services.webhooks import send_webhook_event
from notifications.services import notify

from .models import Invoice, InvoiceStatus, Payment, PaymentMethod, PaymentStatus, RecurringInvoiceProfile
from .serializers import (
    ExchangeRateQuerySerializer, InvoiceCreateSerializer, InvoiceDetailSerializer,
    InvoiceListSerializer, MarkPaidSerializer, PublicInvoiceSerializer, RecurringInvoiceProfileSerializer,
)
from .services.exchange_rates import fetch_exchange_rate_to_inr
from .services.invoices import create_invoice
from .services.notifications import send_invoice_email, send_payment_confirmation_email
from .services.payments import create_payment_link, verify_webhook_signature
from .services.pdf import generate_invoice_pdf

logger = logging.getLogger(__name__)


SUBSCRIPTION_STATUS_BY_EVENT = {
    "subscription.activated": SubscriptionStatus.ACTIVE,
    "subscription.charged": SubscriptionStatus.ACTIVE,
    "subscription.halted": SubscriptionStatus.PAST_DUE,
    "subscription.cancelled": SubscriptionStatus.CANCELLED,
    "subscription.completed": SubscriptionStatus.CANCELLED,
}


def _handle_subscription_event(payload, new_status):
    entity = payload["payload"]["subscription"]["entity"]
    subscription = (
        Subscription.objects.select_related("user__referred_by")
        .filter(razorpay_subscription_id=entity["id"])
        .first()
    )
    if subscription is None:
        logger.warning("Webhook for unknown Razorpay subscription id %s", entity["id"])
        return

    subscription.status = new_status
    update_fields = ["status", "updated_at"]
    if entity.get("current_end"):
        subscription.current_period_end = timezone.make_aware(
            timezone.datetime.fromtimestamp(entity["current_end"])
        )
        update_fields.append("current_period_end")
    subscription.save(update_fields=update_fields)

    # Reward the referrer once, the first time this user ever goes active -
    # `subscription.charged` fires every billing cycle, so this must not
    # re-fire on renewals.
    if (
        new_status == SubscriptionStatus.ACTIVE
        and not subscription.referral_reward_granted
        and subscription.user.referred_by_id
    ):
        grant_referral_reward(subscription.user.referred_by)
        subscription.referral_reward_granted = True
        subscription.save(update_fields=["referral_reward_granted"])


def _invoice_webhook_payload(invoice):
    return {
        "invoice_number": invoice.invoice_number,
        "client_name": invoice.client_name_snapshot,
        "currency": invoice.currency,
        "total_amount": str(invoice.total_amount),
        "status": invoice.status,
        "due_date": str(invoice.due_date),
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }


class InvoiceViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = Invoice.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get("status")
        client_filter = self.request.query_params.get("client")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if client_filter:
            qs = qs.filter(client_id=client_filter)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        if self.action == "create":
            return InvoiceCreateSerializer
        return InvoiceDetailSerializer

    def create(self, request, *args, **kwargs):
        if not can_create_invoice(request.user):
            return Response(
                {
                    "detail": "You've reached the free plan's monthly invoice limit. Upgrade to Pro for unlimited invoices.",
                    "upgrade_required": True,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice = create_invoice(
            user=request.user,
            client=data["client"],
            issue_date=data["issue_date"],
            due_date=data["due_date"],
            currency=data["currency"],
            exchange_rate_to_inr=data["exchange_rate_to_inr"],
            items_data=data["items"],
        )
        out = InvoiceDetailSerializer(invoice, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """FR-6: generate a payment link and email the invoice + link to the client."""
        invoice = self.get_object()

        try:
            link = create_payment_link(invoice)
            invoice.payment_link_url = link["short_url"]
            invoice.razorpay_payment_link_id = link["id"]
        except Exception:
            logger.exception("Razorpay payment link creation failed for invoice %s", invoice.invoice_number)

        invoice.status = InvoiceStatus.SENT
        invoice.sent_at = timezone.now()
        invoice.save()

        send_invoice_email(invoice)
        return Response(InvoiceDetailSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """FR-6: manual 'mark as paid' fallback for payments received outside Razorpay."""
        invoice = self.get_object()
        serializer = MarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Payment.objects.create(
            invoice=invoice,
            amount=serializer.validated_data["amount"],
            payment_date=serializer.validated_data["payment_date"],
            method=PaymentMethod.MANUAL,
            status=PaymentStatus.CAPTURED,
        )
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = timezone.now()
        invoice.save()
        send_webhook_event(invoice.user, "invoice.paid", _invoice_webhook_payload(invoice))
        notify(
            invoice.user, "invoice_paid", f"Invoice {invoice.invoice_number} was marked paid.",
            link_path=f"/invoices/{invoice.id}",
        )
        return Response(InvoiceDetailSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="regenerate-pdf")
    def regenerate_pdf(self, request, pk=None):
        invoice = self.get_object()
        pdf_bytes = generate_invoice_pdf(invoice)
        invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(pdf_bytes), save=True)
        return Response(InvoiceDetailSerializer(invoice, context={"request": request}).data)


class PublicInvoiceView(APIView):
    """No-login client-facing invoice view/pay page (Settings note: permanent, unlike ReportShareLink)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_view"

    def get(self, request, token):
        invoice = get_object_or_404(Invoice, public_view_token=token)
        return Response(PublicInvoiceSerializer(invoice, context={"request": request}).data)


class RecurringInvoiceProfileViewSet(viewsets.ModelViewSet):
    """Phase 4: manage recurring invoice templates that auto-generate real invoices."""

    serializer_class = RecurringInvoiceProfileSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            RecurringInvoiceProfile.objects.filter(user=self.request.user)
            .select_related("client", "last_generated_invoice")
            .prefetch_related("items")
        )


class ExchangeRateView(APIView):
    """Phase 4: suggests a live exchange rate to INR for a foreign invoice currency."""

    def get(self, request):
        query = ExchangeRateQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        currency = query.validated_data["currency"]

        try:
            rate = fetch_exchange_rate_to_inr(currency)
        except Exception:
            logger.exception("Live exchange rate lookup failed for %s", currency)
            return Response(
                {"detail": "Could not fetch a live exchange rate. Please enter it manually."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"currency": currency, "exchange_rate_to_inr": str(rate)})


class RazorpayWebhookView(APIView):
    """
    Receives Razorpay events (e.g. payment_link.paid). No auth - Razorpay
    calls this directly - trust is established purely via signature
    verification (PRD NFR, Section 5).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not verify_webhook_signature(request.body, signature):
            return Response({"detail": "invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        payload = json.loads(request.body)
        event = payload.get("event")

        if event == "payment_link.paid":
            entity = payload["payload"]["payment_link"]["entity"]
            reference_id = entity.get("reference_id")
            invoice = Invoice.objects.filter(invoice_number=reference_id).first()
            if invoice and invoice.status != InvoiceStatus.PAID:
                payment_entity = payload["payload"].get("payment", {}).get("entity", {})
                Payment.objects.create(
                    invoice=invoice,
                    amount=entity["amount_paid"] / 100,
                    payment_date=timezone.now(),
                    method=PaymentMethod.RAZORPAY,
                    razorpay_payment_id=payment_entity.get("id", ""),
                    status=PaymentStatus.CAPTURED,
                )
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = timezone.now()
                invoice.save()
                send_payment_confirmation_email(invoice)
                send_webhook_event(invoice.user, "invoice.paid", _invoice_webhook_payload(invoice))
                notify(
                    invoice.user, "invoice_paid", f"Invoice {invoice.invoice_number} was paid via Razorpay.",
                    link_path=f"/invoices/{invoice.id}",
                )

        elif event in SUBSCRIPTION_STATUS_BY_EVENT:
            _handle_subscription_event(payload, SUBSCRIPTION_STATUS_BY_EVENT[event])

        return Response({"status": "ok"})
