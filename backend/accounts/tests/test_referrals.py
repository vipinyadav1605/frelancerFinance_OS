from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User


class RegistrationReferralTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def test_every_user_gets_a_unique_referral_code(self):
        user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.assertTrue(user.referral_code)

    def test_registering_with_a_valid_referral_code_sets_referred_by(self):
        referrer = User.objects.create_user(email="riya@example.com", password="testpass123")
        response = self.api.post("/api/auth/register/", {
            "email": "amit@example.com", "password": "testpass123",
            "referred_by_code": referrer.referral_code,
        })
        self.assertEqual(response.status_code, 201)
        new_user = User.objects.get(email="amit@example.com")
        self.assertEqual(new_user.referred_by_id, referrer.id)

    def test_registering_with_an_unknown_referral_code_is_silently_ignored(self):
        response = self.api.post("/api/auth/register/", {
            "email": "amit@example.com", "password": "testpass123",
            "referred_by_code": "not-a-real-code",
        })
        self.assertEqual(response.status_code, 201)
        new_user = User.objects.get(email="amit@example.com")
        self.assertIsNone(new_user.referred_by)

    def test_registering_with_no_referral_code_works_as_before(self):
        response = self.api.post("/api/auth/register/", {
            "email": "amit@example.com", "password": "testpass123",
        })
        self.assertEqual(response.status_code, 201)


class ReferralStatusApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_returns_own_code_and_zero_referrals(self):
        response = self.api.get("/api/auth/referral/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["referral_code"], self.user.referral_code)
        self.assertEqual(response.data["referral_count"], 0)

    def test_counts_referred_signups(self):
        User.objects.create_user(email="amit@example.com", password="testpass123", referred_by=self.user)
        response = self.api.get("/api/auth/referral/")
        self.assertEqual(response.data["referral_count"], 1)

    def test_requires_authentication(self):
        response = APIClient().get("/api/auth/referral/")
        self.assertEqual(response.status_code, 401)
