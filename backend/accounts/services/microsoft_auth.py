"""
Microsoft Sign-In (Entra ID / Azure AD): the frontend uses MSAL.js to get an
ID token via a popup, then hands it to us to verify and turn into our own
JWT pair - the same shape as Google Sign-In, just a different token issuer.

Requires MICROSOFT_OAUTH_CLIENT_ID to be set (create an "App registration" in
the Azure Portal under Microsoft Entra ID - this project can't create that
for you, it's tied to your own Azure account). Until it's set,
verify_microsoft_id_token always raises MicrosoftAuthNotConfigured so the
feature fails loudly and clearly rather than silently accepting garbage
tokens.

Verification is JWKS-based (fetch Microsoft's current signing keys, verify
the token's signature against them) rather than a fixed shared secret, since
Microsoft rotates its signing keys - PyJWT's PyJWKClient handles fetching
and caching the right key by the token's "kid" header.
"""

from django.conf import settings
import jwt
from jwt import PyJWKClient

from .oauth_common import get_or_create_oauth_user

JWKS_URL = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
ISSUER_PREFIX = "https://login.microsoftonline.com/"

_jwk_client = None


class MicrosoftAuthNotConfigured(Exception):
    pass


class InvalidMicrosoftToken(Exception):
    pass


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(JWKS_URL)
    return _jwk_client


def verify_microsoft_id_token(raw_id_token: str) -> dict:
    if not settings.MICROSOFT_OAUTH_CLIENT_ID:
        raise MicrosoftAuthNotConfigured(
            "Microsoft sign-in is not configured on this server (MICROSOFT_OAUTH_CLIENT_ID is unset)."
        )
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(raw_id_token)
        payload = jwt.decode(
            raw_id_token, signing_key.key, algorithms=["RS256"],
            audience=settings.MICROSOFT_OAUTH_CLIENT_ID,
            options={"verify_iss": False},  # multi-tenant "common" endpoint issues a per-tenant iss
        )
    except jwt.PyJWTError as exc:
        raise InvalidMicrosoftToken(str(exc)) from exc

    if not str(payload.get("iss", "")).startswith(ISSUER_PREFIX):
        raise InvalidMicrosoftToken("Unexpected token issuer.")

    email = payload.get("email") or payload.get("preferred_username")
    if not email:
        raise InvalidMicrosoftToken("Token did not include an email address.")

    return {"email": email, "name": payload.get("name", "")}


def get_or_create_user_from_microsoft(email: str, name: str):
    return get_or_create_oauth_user(email, name)
