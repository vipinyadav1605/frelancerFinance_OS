from django.utils import timezone

from invoicing.models import Invoice

from ..models import FREE_TIER_MONTHLY_INVOICE_LIMIT


def is_pro(user) -> bool:
    subscription = getattr(user, "subscription", None)
    if subscription is None or not subscription.is_pro:
        return False
    # A real paid subscription's current_period_end is refreshed every
    # billing cycle by the Razorpay webhook (see invoicing/views.py), so this
    # never falsely expires an actively-paying user. It does, however, let a
    # referral-reward grant (see services/referrals.py) self-expire without
    # any extra cron job.
    if subscription.current_period_end is None:
        return True
    return subscription.current_period_end >= timezone.now()


def invoices_created_this_month(user) -> int:
    start_of_month = timezone.localdate().replace(day=1)
    return Invoice.objects.filter(user=user, created_at__date__gte=start_of_month).count()


def can_create_invoice(user) -> bool:
    if is_pro(user):
        return True
    return invoices_created_this_month(user) < FREE_TIER_MONTHLY_INVOICE_LIMIT


def usage_summary(user) -> dict:
    return {
        "is_pro": is_pro(user),
        "invoices_this_month": invoices_created_this_month(user),
        "free_tier_monthly_invoice_limit": FREE_TIER_MONTHLY_INVOICE_LIMIT,
    }
