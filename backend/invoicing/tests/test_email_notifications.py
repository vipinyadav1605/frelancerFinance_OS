from datetime import date
from decimal import Decimal

from django.core import mail
from django.test import TestCase

from accounts.models import BusinessProfile, NotificationPreference, User
from clients.models import Client
from invoicing.models import Invoice, InvoiceStatus, TaxType
from invoicing.services.notifications import send_invoice_email, send_payment_confirmation_email


class EmailSignoffTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.client_obj = Client.objects.create(
            user=self.user, name="Mumbai Co", email="mumbai@example.com", country="India", state="Maharashtra",
        )

    def _make_invoice(self):
        return Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_email_snapshot=self.client_obj.email,
            client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("10000"), total_amount=Decimal("11800"),
            status=InvoiceStatus.DRAFT,
        )

    def test_default_signoff_uses_business_name(self):
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        send_invoice_email(self._make_invoice())
        self.assertIn("Thanks,\nRiya Design", mail.outbox[0].body)

    def test_custom_signoff_overrides_the_default(self):
        BusinessProfile.objects.create(
            user=self.user, business_name="Riya Design", state="Maharashtra",
            email_signoff="Warm regards,\nRiya\n+91-9999999999",
        )
        send_invoice_email(self._make_invoice())
        self.assertIn("Warm regards,\nRiya\n+91-9999999999", mail.outbox[0].body)
        self.assertNotIn("Thanks,\nRiya Design", mail.outbox[0].body)


class PaymentConfirmationPreferenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        self.invoice = Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("10000"), total_amount=Decimal("11800"),
            status=InvoiceStatus.PAID,
        )

    def test_sent_by_default(self):
        send_payment_confirmation_email(self.invoice)
        self.assertEqual(len(mail.outbox), 1)

    def test_skipped_when_preference_is_off(self):
        NotificationPreference.objects.filter(user=self.user).update(payment_confirmation_emails=False)
        # Re-fetch, rather than reuse self.invoice/self.user: signing up already
        # populated self.user's cached reverse relation via the post_save signal's
        # own NotificationPreference.objects.create() call, and that in-memory cache
        # wouldn't reflect the .update() above. A real request never hits this - it
        # always builds a fresh User instance per request - so mirror that here too.
        fresh_invoice = Invoice.objects.get(pk=self.invoice.pk)
        send_payment_confirmation_email(fresh_invoice)
        self.assertEqual(len(mail.outbox), 0)
