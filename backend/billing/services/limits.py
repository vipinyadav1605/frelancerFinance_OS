from django.utils import timezone

from invoicing.models import Invoice

from ..models import FREE_TIER_MONTHLY_INVOICE_LIMIT


def is_pro(user) -> bool:
    subscription = getattr(user, "subscription", None)
    return subscription is not None and subscription.is_pro


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
