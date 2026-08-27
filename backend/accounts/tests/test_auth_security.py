from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services.password_reset import reset_password_with_token, send_password_reset_email


class LoginAndLogoutTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache - isolate each test's count
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "testpass123"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_logout_blacklists_the_refresh_token(self):
        login = self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "testpass123"})
        access, refresh = login.data["access"], login.data["refresh"]

        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_response = self.api.post("/api/auth/logout/", {"refresh": refresh})
        self.assertEqual(logout_response.status_code, 204)

        refresh_attempt = self.api.post("/api/auth/refresh/", {"refresh": refresh})
        self.assertEqual(refresh_attempt.status_code, 401)

    def test_logout_with_garbage_token_still_succeeds(self):
        self.api.force_authenticate(user=self.user)
        response = self.api.post("/api/auth/logout/", {"refresh": "not-a-real-token"})
        self.assertEqual(response.status_code, 204)

    def test_login_is_rate_limited(self):
        for _ in range(10):
            self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "wrong"})
        response = self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, 429)


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="riya@example.com", password="oldpass123")
        self.api = APIClient()

    def test_request_for_registered_email_sends_a_mail_with_a_reset_link(self):
        send_password_reset_email("riya@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password", mail.outbox[0].body)

    def test_request_for_unregistered_email_sends_nothing_but_does_not_error(self):
        send_password_reset_email("nobody@example.com")  # must not raise
        self.assertEqual(len(mail.outbox), 0)

    def test_api_request_always_returns_200_regardless_of_whether_email_exists(self):
        registered = self.api.post("/api/auth/password-reset/", {"email": "riya@example.com"})
        unregistered = self.api.post("/api/auth/password-reset/", {"email": "nobody@example.com"})
        self.assertEqual(registered.status_code, 200)
        self.assertEqual(unregistered.status_code, 200)

    def test_valid_token_resets_the_password(self):
        with patch("accounts.services.password_reset.default_token_generator") as mock_gen:
            mock_gen.make_token.return_value = "tok"
            mock_gen.check_token.return_value = True
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode
            uid = urlsafe_base64_encode(force_bytes(self.user.pk))

            ok = reset_password_with_token(uid=uid, token="tok", new_password="newpass456")
        self.assertTrue(ok)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456"))

    def test_invalid_token_does_not_reset_the_password(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        ok = reset_password_with_token(uid=uid, token="bogus-token", new_password="newpass456")
        self.assertFalse(ok)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))

    def test_garbage_uid_does_not_crash(self):
        ok = reset_password_with_token(uid="not-valid-base64!!", token="tok", new_password="newpass456")
        self.assertFalse(ok)

    def test_full_flow_via_api(self):
        request_response = self.api.post("/api/auth/password-reset/", {"email": "riya@example.com"})
        self.assertEqual(request_response.status_code, 200)
        body = mail.outbox[0].body
        # Link looks like http://.../reset-password/<uid>/<token>/
        link = [line for line in body.splitlines() if "reset-password" in line][0].strip()
        uid, token = link.rstrip("/").split("/")[-2:]

        confirm_response = self.api.post("/api/auth/password-reset-confirm/", {
            "uid": uid, "token": token, "new_password": "brandnewpass789",
        })
        self.assertEqual(confirm_response.status_code, 200)

        login_response = self.api.post("/api/auth/login/", {"email": "riya@example.com", "password": "brandnewpass789"})
        self.assertEqual(login_response.status_code, 200)


class GstinPanValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_valid_gstin_and_pan_are_accepted(self):
        response = self.api.put("/api/auth/business-profile/", {
            "business_name": "Riya Design", "pan": "ABCDE1234F", "gstin": "27AAAAA0000A1Z5",
            "is_gst_registered": True, "address": "Mumbai", "state": "Maharashtra",
            "invoice_prefix": "INV", "lut_reference": "",
        })
        self.assertEqual(response.status_code, 200)

    def test_malformed_gstin_is_rejected(self):
        response = self.api.put("/api/auth/business-profile/", {
            "business_name": "Riya Design", "pan": "ABCDE1234F", "gstin": "not-a-gstin",
            "is_gst_registered": True, "address": "Mumbai", "state": "Maharashtra",
            "invoice_prefix": "INV", "lut_reference": "",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("gstin", response.data)

    def test_malformed_pan_is_rejected(self):
        response = self.api.put("/api/auth/business-profile/", {
            "business_name": "Riya Design", "pan": "12345", "gstin": "",
            "is_gst_registered": False, "address": "Mumbai", "state": "Maharashtra",
            "invoice_prefix": "INV", "lut_reference": "",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("pan", response.data)

    def test_blank_gstin_and_pan_are_allowed(self):
        response = self.api.put("/api/auth/business-profile/", {
            "business_name": "Riya Design", "pan": "", "gstin": "",
            "is_gst_registered": False, "address": "Mumbai", "state": "Maharashtra",
            "invoice_prefix": "INV", "lut_reference": "",
        })
        self.assertEqual(response.status_code, 200)
