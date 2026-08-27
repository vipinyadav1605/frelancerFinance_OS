"""
Phase 5: lets automation scripts authenticate with a personal API key instead
of a JWT access token (which expires every 30 minutes - unworkable for a
long-running cron/Zapier-style integration).

Usage: `Authorization: Api-Key ffos_xxxxxxxx...`
"""

from django.utils import timezone
from rest_framework import authentication, exceptions

from .services.api_keys import resolve_api_key


class ApiKeyAuthentication(authentication.BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header or not header.startswith(f"{self.keyword} "):
            return None

        raw_key = header[len(self.keyword) + 1:].strip()
        api_key = resolve_api_key(raw_key)
        if api_key is None:
            raise exceptions.AuthenticationFailed("Invalid or revoked API key.")

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])
        return (api_key.user, api_key)
