"""Generates real invoices from RecurringInvoiceProfile templates (Phase 4)."""

import calendar
import logging
from datetime import timedelta

from django.utils import timezone

from invoicing.models import InvoiceStatus, RecurringFrequency, RecurringInvoiceProfile

from .invoices import create_invoice
from .notifications import send_invoice_email
from .payments import create_payment_link

logger = logging.getLogger(__name__)


def _add_months(d, months):
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def next_run_after(current_date, frequency):
    if frequency == RecurringFrequency.WEEKLY:
        return current_date + timedelta(weeks=1)
    if frequency == RecurringFrequency.MONTHLY:
        return _add_months(current_date, 1)
    if frequency == RecurringFrequency.QUARTERLY:
        return _add_months(current_date, 3)
    raise ValueError(f"Unknown recurring frequency: {frequency}")


def generate_due_invoices(*, today=None):
    """
    Generates one invoice per active profile whose next_run_date has arrived,
    then advances that profile's schedule by one cycle. If a profile has been
    overdue for longer than one cycle (e.g. the scheduler was down), only the
    latest cycle is generated - past cycles are not backfilled.
    """
    today = today or timezone.localdate()
    due_profiles = RecurringInvoiceProfile.objects.filter(is_active=True, next_run_date__lte=today)

    created = []
    for profile in due_profiles:
        items_data = [
            {
                "description": item.description,
                "hsn_sac_code": item.hsn_sac_code,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "tax_rate_percent": item.tax_rate_percent,
            }
            for item in profile.items.all()
        ]
        if not items_data:
            logger.warning("Skipping recurring profile %s - it has no line items.", profile.id)
            continue

        invoice = create_invoice(
            user=profile.user,
            client=profile.client,
            issue_date=today,
            due_date=today + timedelta(days=profile.due_in_days),
            currency=profile.currency,
            exchange_rate_to_inr=profile.exchange_rate_to_inr,
            items_data=items_data,
        )

        if profile.auto_send:
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

        profile.last_generated_invoice = invoice
        profile.next_run_date = next_run_after(profile.next_run_date, profile.frequency)
        profile.save(update_fields=["last_generated_invoice", "next_run_date", "updated_at"])
        created.append(invoice)

    return created
