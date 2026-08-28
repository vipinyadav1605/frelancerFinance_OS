"""Email notifications for the invoice lifecycle (FR-6, Phase 3 reminders)."""

from django.core.mail import EmailMessage
from django.utils import timezone

from .pdf import generate_invoice_pdf


def _signoff(invoice):
    """Settings > Business lets a user override the default sign-off text."""
    profile = invoice.user.business_profile
    return profile.email_signoff or f"Thanks,\n{profile.business_name}"


def send_invoice_email(invoice):
    subject = f"Invoice {invoice.invoice_number} from {invoice.user.business_profile.business_name}"
    body_lines = [
        f"Hi {invoice.client_name_snapshot},",
        "",
        f"Please find attached invoice {invoice.invoice_number} "
        f"for {invoice.currency} {invoice.total_amount:.2f}, due {invoice.due_date}.",
    ]
    if invoice.payment_link_url:
        body_lines += ["", f"You can pay securely here: {invoice.payment_link_url}"]
    body_lines += ["", _signoff(invoice)]

    email = EmailMessage(
        subject=subject,
        body="\n".join(body_lines),
        to=[invoice.client_email_snapshot] if invoice.client_email_snapshot else [],
    )
    email.attach(
        f"{invoice.invoice_number}.pdf", generate_invoice_pdf(invoice), "application/pdf"
    )
    email.send(fail_silently=False)


def send_overdue_reminder_email(invoice):
    """Phase 3: automated payment reminder for overdue invoices."""
    days_overdue = (timezone.localdate() - invoice.due_date).days
    subject = f"Reminder: invoice {invoice.invoice_number} is overdue"
    body_lines = [
        f"Hi {invoice.client_name_snapshot},",
        "",
        f"This is a friendly reminder that invoice {invoice.invoice_number} for "
        f"{invoice.currency} {invoice.total_amount:.2f} was due on {invoice.due_date} "
        f"({days_overdue} day(s) ago) and has not yet been marked as paid.",
    ]
    if invoice.payment_link_url:
        body_lines += ["", f"You can pay securely here: {invoice.payment_link_url}"]
    body_lines += ["", _signoff(invoice)]

    email = EmailMessage(
        subject=subject,
        body="\n".join(body_lines),
        to=[invoice.client_email_snapshot] if invoice.client_email_snapshot else [],
    )
    email.send(fail_silently=False)


def send_payment_confirmation_email(invoice):
    """Togglable via Settings > Notifications (accounts.models.NotificationPreference)."""
    preference = getattr(invoice.user, "notification_preference", None)
    if preference is not None and not preference.payment_confirmation_emails:
        return

    EmailMessage(
        subject=f"Payment received for invoice {invoice.invoice_number}",
        body=(
            f"Good news - payment of {invoice.currency} {invoice.total_amount:.2f} "
            f"for invoice {invoice.invoice_number} has been received."
        ),
        to=[invoice.user.email],
    ).send(fail_silently=False)
