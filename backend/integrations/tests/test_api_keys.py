from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from integrations.models import ApiKey
from integrations.services.api_keys import create_api_key, resolve_api_key


class CreateAndResolveApiKeyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")

    def test_created_key_resolves_to_the_owning_user(self):
        api_key, full_key = create_api_key(user=self.user, name="Zapier")
        resolved = resolve_api_key(full_key)
        self.assertEqual(resolved.id, api_key.id)
        self.assertEqual(resolved.user, self.user)

    def test_full_key_is_never_stored_in_the_database(self):
        _, full_key = create_api_key(user=self.user, name="Zapier")
        self.assertFalse(ApiKey.objects.filter(key_hash=full_key).exists())

    def test_garbage_key_does_not_resolve(self):
        self.assertIsNone(resolve_api_key("not-a-real-key"))

    def test_revoked_key_does_not_resolve(self):
        api_key, full_key = create_api_key(user=self.user, name="Zapier")
        api_key.revoked_at = api_key.created_at
        api_key.save()
        self.assertIsNone(resolve_api_key(full_key))


class ApiKeyAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="riya@example.com", password="testpass123")
        self.client_http = APIClient()

    def test_api_key_authenticates_requests_to_a_jwt_protected_endpoint(self):
        _, full_key = create_api_key(user=self.user, name="Zapier")
        self.client_http.credentials(HTTP_AUTHORIZATION=f"Api-Key {full_key}")
        response = self.client_http.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_invalid_api_key_is_rejected(self):
        self.client_http.credentials(HTTP_AUTHORIZATION="Api-Key ffos_bogus")
        response = self.client_http.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_creating_a_key_via_the_api_returns_the_raw_key_once(self):
        self.client_http.force_authenticate(user=self.user)
        response = self.client_http.post("/api/api-keys/", {"name": "My Script"})
        self.assertEqual(response.status_code, 201)
        self.assertIn("key", response.data)
        self.assertTrue(response.data["key"].startswith("ffos_"))

    def test_listing_keys_never_exposes_the_raw_key(self):
        self.client_http.force_authenticate(user=self.user)
        self.client_http.post("/api/api-keys/", {"name": "My Script"})
        response = self.client_http.get("/api/api-keys/")
        self.assertNotIn("key", response.data[0])

    def test_deleting_a_key_revokes_rather_than_hard_deletes(self):
        self.client_http.force_authenticate(user=self.user)
        create_response = self.client_http.post("/api/api-keys/", {"name": "My Script"})
        key_id = create_response.data["id"]
        delete_response = self.client_http.delete(f"/api/api-keys/{key_id}/")
        self.assertEqual(delete_response.status_code, 204)
        api_key = ApiKey.objects.get(id=key_id)
        self.assertIsNotNone(api_key.revoked_at)
        self.assertFalse(api_key.is_active)
