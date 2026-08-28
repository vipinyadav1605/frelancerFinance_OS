"""
Google Sign-In: the frontend uses Google Identity Services to get an ID
token, then hands it to us to verify and turn into our own JWT pair.

Requires GOOGLE_OAUTH_CLIENT_ID to be set (a real one, created in Google
Cloud Console under "OAuth 2.0 Client IDs" - this project can't create that
for you, it's tied to your own Google account/project). Until it's set,
verify_google_id_token always raises GoogleAuthNotConfigured so the feature
fails loudly and clearly rather than silently accepting garbage tokens.
"""

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .oauth_common import get_or_create_oauth_user


class GoogleAuthNotConfigured(Exception):
    pass


class InvalidGoogleToken(Exception):
    pass


def verify_google_id_token(raw_id_token: str) -> dict:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise GoogleAuthNotConfigured(
            "Google sign-in is not configured on this server (GOOGLE_OAUTH_CLIENT_ID is unset)."
        )
    try:
        payload = google_id_token.verify_oauth2_token(
            raw_id_token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except ValueError as exc:
        raise InvalidGoogleToken(str(exc)) from exc

    return {"email": payload["email"], "name": payload.get("name", "")}


def get_or_create_user_from_google(email: str, name: str):
    return get_or_create_oauth_user(email, name)
