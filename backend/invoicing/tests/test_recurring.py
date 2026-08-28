from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from accounts.models import BusinessProfile, User
from clients.models import Client
from invoicing.models import RecurringFrequency, RecurringInvoiceItem, RecurringInvoiceProfile
from invoicing.services.recurring import generate_due_invoices, next_run_after


class NextRunAfterTests(TestCase):
    def test_weekly_adds_seven_days(self):
        self.assertEqual(next_run_after(date(2026, 1, 1), RecurringFrequency.WEEKLY), date(2026, 1, 8))

    def test_monthly_advances_one_month(self):
        self.assertEqual(next_run_after(date(2026, 1, 15), RecurringFrequency.MONTHLY), date(2026, 2, 15))

    def test_monthly_clamps_short_months(self):
        # Jan 31 + 1 month -> Feb has no 31st, should clamp to the 28th (2026 is not a leap year).
        self.assertEqual(next_run_after(date(2026, 1, 31), RecurringFrequency.MONTHLY), date(2026, 2, 28))

    def test_quarterly_advances_three_months_and_rolls_over_year(self):
        self.assertEqual(next_run_after(date(2026, 11, 10), RecurringFrequency.QUARTERLY), date(2027, 2, 10))


class GenerateDueInvoicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(
            user=self.user, name="Mumbai Co", email="ap@mumbaico.example", country="India", state="Maharashtra",
        )

    def _make_profile(self, next_run_date, **overrides):
        defaults = dict(
            user=self.user, client=self.client_obj, frequency=RecurringFrequency.MONTHLY,
            next_run_date=next_run_date, due_in_days=14,
        )
        defaults.update(overrides)
        profile = RecurringInvoiceProfile.objects.create(**defaults)
        RecurringInvoiceItem.objects.create(
            profile=profile, description="Monthly retainer", quantity=Decimal("1"),
            unit_price=Decimal("20000"), tax_rate_percent=Decimal("18"),
        )
        return profile

    def test_due_profile_generates_an_invoice_and_advances_schedule(self):
        profile = self._make_profile(date(2026, 6, 1))
        created = generate_due_invoices(today=date(2026, 6, 1))

        self.assertEqual(len(created), 1)
        invoice = created[0]
        self.assertEqual(invoice.client_id, self.client_obj.id)
        self.assertEqual(invoice.subtotal, Decimal("20000.00"))
        self.assertEqual(invoice.due_date, date(2026, 6, 15))

        profile.refresh_from_db()
        self.assertEqual(profile.next_run_date, date(2026, 7, 1))
        self.assertEqual(profile.last_generated_invoice_id, invoice.id)

        from notifications.models import Notification
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, notification_type="recurring_invoice_generated"
            ).exists()
        )

    def test_not_yet_due_profile_is_skipped(self):
        self._make_profile(date(2026, 7, 1))
        created = generate_due_invoices(today=date(2026, 6, 1))
        self.assertEqual(created, [])

    def test_inactive_profile_is_skipped(self):
        self._make_profile(date(2026, 6, 1), is_active=False)
        created = generate_due_invoices(today=date(2026, 6, 1))
        self.assertEqual(created, [])

    def test_profile_with_no_items_is_skipped_without_crashing(self):
        profile = RecurringInvoiceProfile.objects.create(
            user=self.user, client=self.client_obj, frequency=RecurringFrequency.MONTHLY,
            next_run_date=date(2026, 6, 1), due_in_days=14,
        )
        created = generate_due_invoices(today=date(2026, 6, 1))
        self.assertEqual(created, [])
        profile.refresh_from_db()
        self.assertEqual(profile.next_run_date, date(2026, 6, 1))  # untouched

    @patch("invoicing.services.recurring.create_payment_link")
    def test_auto_send_emails_the_client(self, mock_create_link):
        mock_create_link.return_value = {"id": "plink_test", "short_url": "https://rzp.io/test"}
        self._make_profile(date(2026, 6, 1), auto_send=True)
        generate_due_invoices(today=date(2026, 6, 1))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.client_obj.email, mail.outbox[0].to)

    def test_auto_send_false_does_not_email(self):
        self._make_profile(date(2026, 6, 1), auto_send=False)
        generate_due_invoices(today=date(2026, 6, 1))
        self.assertEqual(len(mail.outbox), 0)
