from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import BusinessProfile, NotificationPreference, User
from accounts.services.account_deletion import delete_user_account
from clients.models import Client
from invoicing.models import Invoice, InvoiceStatus, TaxType


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="oldpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_correct_current_password_changes_it(self):
        response = self.api.post("/api/auth/change-password/", {
            "current_password": "oldpass123", "new_password": "newpass456",
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456"))

    def test_wrong_current_password_is_rejected(self):
        response = self.api.post("/api/auth/change-password/", {
            "current_password": "wrongpass", "new_password": "newpass456",
        })
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))


class ChangeEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.other_user = User.objects.create_user(email="other@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_correct_password_changes_email(self):
        response = self.api.post("/api/auth/change-email/", {
            "new_email": "riya.new@example.com", "current_password": "testpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "riya.new@example.com")

    def test_wrong_password_is_rejected(self):
        response = self.api.post("/api/auth/change-email/", {
            "new_email": "riya.new@example.com", "current_password": "wrongpass",
        })
        self.assertEqual(response.status_code, 400)

    def test_cannot_change_to_an_email_already_in_use(self):
        response = self.api.post("/api/auth/change-email/", {
            "new_email": "other@example.com", "current_password": "testpass123",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_email", response.data)


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        Invoice.objects.create(
            user=self.user, client=self.client_obj,
            client_name_snapshot=self.client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("10000"), total_amount=Decimal("10000"),
            status=InvoiceStatus.SENT,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_delete_account_service_removes_everything_without_protected_error(self):
        user_id = self.user.id
        delete_user_account(self.user)  # must not raise ProtectedError
        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertFalse(Client.objects.filter(user_id=user_id).exists())
        self.assertFalse(Invoice.objects.filter(user_id=user_id).exists())

    def test_wrong_password_via_api_does_not_delete_the_account(self):
        response = self.api.post("/api/auth/delete-account/", {"current_password": "wrongpass"})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(id=self.user.id).exists())

    def test_correct_password_via_api_deletes_the_account(self):
        response = self.api.post("/api/auth/delete-account/", {"current_password": "testpass123"})
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())


class NotificationPreferenceApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_defaults_are_all_on(self):
        response = self.api.get("/api/auth/notification-preference/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["payment_confirmation_emails"])
        self.assertTrue(response.data["webhook_failure_emails"])

    def test_can_turn_off_a_preference(self):
        response = self.api.put("/api/auth/notification-preference/", {
            "payment_confirmation_emails": False, "webhook_failure_emails": True,
        })
        self.assertEqual(response.status_code, 200)
        pref = NotificationPreference.objects.get(user=self.user)
        self.assertFalse(pref.payment_confirmation_emails)


class OnboardingStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_brand_new_user_has_nothing_done(self):
        response = self.api.get("/api/auth/onboarding-status/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_business_profile"])
        self.assertFalse(response.data["has_client"])
        self.assertFalse(response.data["has_invoice"])

    def test_status_reflects_actual_progress(self):
        BusinessProfile.objects.create(user=self.user, business_name="Riya Design", state="Maharashtra")
        client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        Invoice.objects.create(
            user=self.user, client=client_obj,
            client_name_snapshot=client_obj.name, client_country_snapshot="India",
            invoice_number="TEST-1", issue_date=date(2026, 6, 10), due_date=date(2026, 6, 24),
            tax_type=TaxType.CGST_SGST, subtotal=Decimal("1000"), total_amount=Decimal("1000"),
            status=InvoiceStatus.DRAFT,
        )
        response = self.api.get("/api/auth/onboarding-status/")
        self.assertTrue(response.data["has_business_profile"])
        self.assertTrue(response.data["has_client"])
        self.assertTrue(response.data["has_invoice"])
        self.assertFalse(response.data["has_sent_invoice"])  # still a draft


class DataExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.client_obj = Client.objects.create(user=self.user, name="Mumbai Co", country="India", state="Maharashtra")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_export_returns_a_zip_with_expected_files(self):
        import zipfile
        from io import BytesIO

        response = self.api.get("/api/auth/data-export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")

        zf = zipfile.ZipFile(BytesIO(response.content))
        names = set(zf.namelist())
        self.assertEqual(names, {"clients.csv", "invoices.csv", "expenses.csv"})
        self.assertIn(b"Mumbai Co", zf.read("clients.csv"))
