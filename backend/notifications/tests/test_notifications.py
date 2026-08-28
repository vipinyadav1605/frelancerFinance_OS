from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from notifications.models import Notification
from notifications.services import notify


class NotifyServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")

    def test_notify_creates_an_unread_notification(self):
        n = notify(self.user, "invoice_paid", "Invoice INV-1 was paid.", link_path="/invoices/1")
        self.assertFalse(n.is_read)
        self.assertEqual(n.message, "Invoice INV-1 was paid.")


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.other_user = User.objects.create_user(email="other@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_list_only_returns_own_notifications(self):
        notify(self.user, "invoice_paid", "Mine")
        notify(self.other_user, "invoice_paid", "Not mine")
        response = self.api.get("/api/notifications/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["message"], "Mine")

    def test_unread_count(self):
        notify(self.user, "invoice_paid", "One")
        notify(self.user, "invoice_overdue", "Two")
        response = self.api.get("/api/notifications/unread-count/")
        self.assertEqual(response.data["unread_count"], 2)

    def test_mark_read_updates_unread_count(self):
        n = notify(self.user, "invoice_paid", "One")
        self.api.post(f"/api/notifications/{n.id}/mark-read/")
        response = self.api.get("/api/notifications/unread-count/")
        self.assertEqual(response.data["unread_count"], 0)

    def test_cannot_mark_another_users_notification_as_read(self):
        n = notify(self.other_user, "invoice_paid", "Not mine")
        response = self.api.post(f"/api/notifications/{n.id}/mark-read/")
        self.assertEqual(response.status_code, 404)

    def test_mark_all_read(self):
        notify(self.user, "invoice_paid", "One")
        notify(self.user, "invoice_overdue", "Two")
        response = self.api.post("/api/notifications/mark-all-read/")
        self.assertEqual(response.data["marked_read"], 2)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)
