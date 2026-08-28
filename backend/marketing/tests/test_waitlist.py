from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from marketing.models import WaitlistSignup


class WaitlistSignupApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def test_signup_creates_a_waitlist_entry(self):
        response = self.api.post("/api/waitlist/", {"email": "amit@example.com"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(WaitlistSignup.objects.filter(email="amit@example.com").exists())

    def test_signup_does_not_require_authentication(self):
        response = self.api.post("/api/waitlist/", {"email": "amit@example.com"})
        self.assertEqual(response.status_code, 201)

    def test_resubmitting_the_same_email_is_idempotent(self):
        self.api.post("/api/waitlist/", {"email": "amit@example.com"})
        response = self.api.post("/api/waitlist/", {"email": "amit@example.com"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(WaitlistSignup.objects.filter(email="amit@example.com").count(), 1)

    def test_invalid_email_is_rejected(self):
        response = self.api.post("/api/waitlist/", {"email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
