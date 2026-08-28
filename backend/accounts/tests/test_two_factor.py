import pyotp
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import TwoFactorAuth, User
from accounts.services import two_factor


class TwoFactorServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")

    def test_start_setup_creates_a_disabled_pending_secret(self):
        result = two_factor.start_setup(self.user)
        self.assertIn("secret", result)
        self.assertIn("qr_code_data_uri", result)
        self.assertTrue(result["qr_code_data_uri"].startswith("data:image/png;base64,"))
        tfa = TwoFactorAuth.objects.get(user=self.user)
        self.assertFalse(tfa.is_enabled)

    def test_confirm_setup_with_valid_code_enables_it(self):
        result = two_factor.start_setup(self.user)
        code = pyotp.TOTP(result["secret"]).now()
        self.assertTrue(two_factor.confirm_setup(self.user, code))
        # Re-fetch rather than reuse self.user: start_setup()'s update_or_create(user=user, ...)
        # caches the pre-enable TwoFactorAuth on self.user's reverse relation (same footgun
        # documented in accounts/services/password_reset.py's test suite) - a real request
        # always gets a fresh User instance, so mirror that here instead of trusting the cache.
        self.assertTrue(two_factor.is_enabled(User.objects.get(pk=self.user.pk)))

    def test_confirm_setup_with_wrong_code_does_not_enable(self):
        two_factor.start_setup(self.user)
        self.assertFalse(two_factor.confirm_setup(self.user, "000000"))
        self.assertFalse(two_factor.is_enabled(self.user))

    def test_confirm_setup_without_a_pending_secret_fails(self):
        self.assertFalse(two_factor.confirm_setup(self.user, "123456"))

    def test_verify_code_works_once_enabled(self):
        result = two_factor.start_setup(self.user)
        two_factor.confirm_setup(self.user, pyotp.TOTP(result["secret"]).now())
        fresh_user = User.objects.get(pk=self.user.pk)
        self.assertTrue(two_factor.verify_code(fresh_user, pyotp.TOTP(result["secret"]).now()))

    def test_disable_removes_the_record(self):
        result = two_factor.start_setup(self.user)
        two_factor.confirm_setup(self.user, pyotp.TOTP(result["secret"]).now())
        two_factor.disable(self.user)
        self.assertFalse(TwoFactorAuth.objects.filter(user=self.user).exists())


class TwoFactorApiAndLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()

    def _enable_2fa(self):
        self.api.force_authenticate(user=self.user)
        setup = self.api.post("/api/auth/2fa/setup/").data
        code = pyotp.TOTP(setup["secret"]).now()
        self.api.post("/api/auth/2fa/confirm/", {"code": code})
        self.api.force_authenticate(user=None)
        return setup["secret"]

    def test_login_without_2fa_enabled_succeeds_normally(self):
        response = self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "testpass123"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_login_with_2fa_enabled_requires_otp_code(self):
        self._enable_2fa()
        response = self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "testpass123"})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.data.get("two_factor_required"))

    def test_login_with_correct_otp_code_succeeds(self):
        secret = self._enable_2fa()
        code = pyotp.TOTP(secret).now()
        response = self.api.post("/api/auth/login/", {
            "email": "riya@example.com", "password": "testpass123", "otp_code": code,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_login_with_wrong_otp_code_fails(self):
        self._enable_2fa()
        response = self.api.post("/api/auth/login/", {
            "email": "riya@example.com", "password": "testpass123", "otp_code": "000000",
        })
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access", response.data)

    def test_status_endpoint_reflects_enabled_state(self):
        self._enable_2fa()
        # force_authenticate injects the exact object given, unlike real JWT auth which
        # re-queries the user fresh per request - re-fetch so this test doesn't see the
        # stale pre-enable TwoFactorAuth cached on self.user by _enable_2fa()'s setup call.
        self.api.force_authenticate(user=User.objects.get(pk=self.user.pk))
        response = self.api.get("/api/auth/2fa/status/")
        self.assertTrue(response.data["is_enabled"])

    def test_disable_requires_correct_password(self):
        self._enable_2fa()
        self.api.force_authenticate(user=User.objects.get(pk=self.user.pk))
        wrong = self.api.post("/api/auth/2fa/disable/", {"current_password": "wrong"})
        self.assertEqual(wrong.status_code, 400)

        right = self.api.post("/api/auth/2fa/disable/", {"current_password": "testpass123"})
        self.assertEqual(right.status_code, 200)
        self.assertFalse(TwoFactorAuth.objects.filter(user=self.user, is_enabled=True).exists())
