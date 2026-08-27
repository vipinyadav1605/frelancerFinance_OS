"""
Phase 4: generates real invoices from active RecurringInvoiceProfile
templates whose next_run_date has arrived. Run daily via the hosting
platform's cron feature, alongside update_overdue_invoices /
send_payment_reminders.
"""

from django.core.management.base import BaseCommand

from invoicing.services.recurring import generate_due_invoices


class Command(BaseCommand):
    help = "Generates invoices for recurring profiles whose next_run_date has arrived."

    def handle(self, *args, **options):
        created = generate_due_invoices()
        for invoice in created:
            self.stdout.write(f"Generated {invoice.invoice_number} for {invoice.client_name_snapshot}")
        self.stdout.write(self.style.SUCCESS(f"Generated {len(created)} invoice(s) from recurring profiles."))
