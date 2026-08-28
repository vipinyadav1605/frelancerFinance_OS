"""
Razorpay Subscriptions for the Pro plan. Requires a Plan already created in
the Razorpay Dashboard (Subscriptions > Plans) - this app can't create that
for you, it's tied to your own Razorpay account. Until
RAZORPAY_PRO_MONTHLY_PLAN_ID is set, create_subscription raises
BillingNotConfigured so the upgrade button fails loudly and clearly instead
of silently doing nothing.
"""

import razorpay
from django.conf import settings

# Razorpay requires a finite total_count of billing cycles for a
# subscription - there's no true "forever" option. 120 monthly cycles (10
# years) is the conventional stand-in for "until the customer cancels".
TOTAL_BILLING_CYCLES = 120


class BillingNotConfigured(Exception):
    pass


def _client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_subscription(user) -> dict:
    if not settings.RAZORPAY_PRO_MONTHLY_PLAN_ID:
        raise BillingNotConfigured(
            "Upgrading isn't configured on this server yet (RAZORPAY_PRO_MONTHLY_PLAN_ID is unset)."
        )

    subscription = _client().subscription.create({
        "plan_id": settings.RAZORPAY_PRO_MONTHLY_PLAN_ID,
        "customer_notify": 1,
        "total_count": TOTAL_BILLING_CYCLES,
        "notes": {"user_id": str(user.id), "email": user.email},
    })
    return {"id": subscription["id"], "short_url": subscription["short_url"]}


def cancel_subscription(razorpay_subscription_id: str) -> None:
    _client().subscription.cancel(razorpay_subscription_id)
