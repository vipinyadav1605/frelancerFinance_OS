"""
Growth loop reward: every user has a shareable `/register?ref=<code>` link
(User.referral_code). When someone who signed up through that link upgrades
to Pro for the first time, the referrer gets a free month of Pro too.

Triggered once, from invoicing.views._handle_subscription_event, guarded by
Subscription.referral_reward_granted so a later `subscription.charged`
webhook (fired every billing cycle) doesn't reward the same referral twice.
"""

from datetime import timedelta

from django.utils import timezone

from notifications.services import notify

from ..models import Subscription, SubscriptionStatus

REFERRAL_REWARD_DAYS = 30


def grant_referral_reward(referrer):
    subscription, _ = Subscription.objects.get_or_create(user=referrer)
    now = timezone.now()
    # Stack on top of an existing active period rather than shortening it.
    if subscription.status == SubscriptionStatus.ACTIVE and subscription.current_period_end and subscription.current_period_end > now:
        base = subscription.current_period_end
    else:
        base = now

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_end = base + timedelta(days=REFERRAL_REWARD_DAYS)
    subscription.save(update_fields=["status", "current_period_end", "updated_at"])

    notify(
        referrer, "referral_reward_granted",
        "Someone you referred just upgraded to Pro - you got 30 free days of Pro as a thank you.",
        link_path="/settings",
    )
