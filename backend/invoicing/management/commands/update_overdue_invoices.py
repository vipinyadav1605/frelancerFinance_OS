"""
FR-6, criterion 3: mark sent-but-unpaid invoices as overdue once their due
date has passed. Run via the hosting platform's scheduled-job feature
(Document 2, Section 2.3: "cron first, Celery+Redis later").

    python manage.py update_overdue_invoices
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from integrations.services.webhooks import send_webhook_event
from invoicing.models import Invoice, InvoiceStatus


class Command(BaseCommand):
    help = "Marks sent invoices past their due date as overdue."

    def handle(self, *args, **options):
        due_invoices = list(
            Invoice.objects.filter(status=InvoiceStatus.SENT, due_date__lt=timezone.localdate())
        )
        for invoice in due_invoices:
            invoice.status = InvoiceStatus.OVERDUE
            invoice.save(update_fields=["status", "updated_at"])
            send_webhook_event(invoice.user, "invoice.overdue", {
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client_name_snapshot,
                "currency": invoice.currency,
                "total_amount": str(invoice.total_amount),
                "due_date": str(invoice.due_date),
            })
        self.stdout.write(self.style.SUCCESS(f"Marked {len(due_invoices)} invoice(s) as overdue."))
