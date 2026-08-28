import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UsageSummarySerializer
from .services.limits import usage_summary
from .services.razorpay_subscriptions import BillingNotConfigured, cancel_subscription, create_subscription

logger = logging.getLogger(__name__)


class BillingStatusView(APIView):
    """Settings > Billing: current plan + this month's usage against the free tier."""

    def get(self, request):
        return Response(UsageSummarySerializer(usage_summary(request.user)).data)


class SubscribeView(APIView):
    """Starts a Razorpay-hosted subscription checkout for the Pro plan."""

    def post(self, request):
        from .models import Subscription

        try:
            result = create_subscription(request.user)
        except BillingNotConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        Subscription.objects.update_or_create(
            user=request.user,
            defaults={"razorpay_subscription_id": result["id"]},
            # status stays "cancelled" until the subscription.activated webhook fires -
            # the user hasn't actually paid yet, they've just started checkout.
        )
        return Response({"short_url": result["short_url"]})


class CancelSubscriptionView(APIView):
    def post(self, request):
        subscription = getattr(request.user, "subscription", None)
        if subscription is None or not subscription.razorpay_subscription_id:
            return Response({"detail": "No active subscription to cancel."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cancel_subscription(subscription.razorpay_subscription_id)
        except Exception:
            logger.exception("Razorpay subscription cancellation failed for user %s", request.user.id)
            return Response({"detail": "Could not cancel via Razorpay - try again shortly."}, status=502)

        return Response({"detail": "Subscription cancelled."})
