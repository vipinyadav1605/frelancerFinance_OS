"""
Phase 3: automated payment reminder emails for overdue invoices. Run
periodically (e.g. daily) via the hosting platform's cron feature, right
after `update_overdue_invoices` so newly-overdue invoices get their first
reminder the same run.

Sends at most one reminder every REMINDER_INTERVAL_DAYS per invoice, so this
is safe to run daily without spamming clients.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from invoicing.models import Invoice, InvoiceStatus
from invoicing.services.notifications import send_overdue_reminder_email

REMINDER_INTERVAL_DAYS = 3


class Command(BaseCommand):
    help = "Sends a payment reminder email for overdue invoices not reminded in the last few days."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=REMINDER_INTERVAL_DAYS)
        due_for_reminder = Invoice.objects.filter(
            status=InvoiceStatus.OVERDUE
        ).filter(
            Q(last_reminder_sent_at__isnull=True) | Q(last_reminder_sent_at__lt=cutoff)
        ).exclude(client_email_snapshot="")

        sent = 0
        for invoice in due_for_reminder:
            try:
                send_overdue_reminder_email(invoice)
                invoice.last_reminder_sent_at = timezone.now()
                invoice.save(update_fields=["last_reminder_sent_at"])
                sent += 1
            except Exception as exc:  # noqa: BLE001 - keep going for the rest of the batch
                self.stderr.write(f"Failed to send reminder for {invoice.invoice_number}: {exc}")

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} overdue payment reminder(s)."))
