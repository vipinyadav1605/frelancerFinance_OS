"""
GitHub Sign-In: unlike Google/Microsoft, GitHub's OAuth flow can't hand the
frontend a verifiable ID token directly - it's a classic Authorization Code
flow that requires a client *secret* to exchange, so the exchange must
happen here, server-side, never in the browser.

Frontend flow: redirect the browser to GitHub's authorize URL -> GitHub
redirects back to our frontend's callback route with `?code=...` -> the
frontend POSTs that code here -> we exchange it for a GitHub access token,
then use that token to fetch the user's profile and verified primary email.

Requires GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET (create an
"OAuth App" at https://github.com/settings/developers - this project can't
create that for you, it's tied to your own GitHub account).
"""

from django.conf import settings
import requests

from .oauth_common import get_or_create_oauth_user

TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
EMAILS_URL = "https://api.github.com/user/emails"
REQUEST_TIMEOUT_SECONDS = 10


class GitHubAuthNotConfigured(Exception):
    pass


class InvalidGitHubCode(Exception):
    pass


def _primary_verified_email(emails: list[dict]) -> str:
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            return entry["email"]
    for entry in emails:  # fall back to any verified address if none is flagged primary
        if entry.get("verified"):
            return entry["email"]
    return ""


def exchange_github_code_for_profile(code: str) -> dict:
    if not settings.GITHUB_OAUTH_CLIENT_ID or not settings.GITHUB_OAUTH_CLIENT_SECRET:
        raise GitHubAuthNotConfigured(
            "GitHub sign-in is not configured on this server (GITHUB_OAUTH_CLIENT_ID/SECRET is unset)."
        )

    token_response = requests.post(
        TOKEN_URL,
        data={
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    token_data = token_response.json() if token_response.ok else {}
    access_token = token_data.get("access_token")
    if not access_token:
        raise InvalidGitHubCode(token_data.get("error_description", "Could not exchange the GitHub code."))

    auth_header = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
    user_response = requests.get(USER_URL, headers=auth_header, timeout=REQUEST_TIMEOUT_SECONDS)
    if not user_response.ok:
        raise InvalidGitHubCode("Could not fetch the GitHub profile for this token.")
    profile = user_response.json()

    email = profile.get("email") or ""
    if not email:
        # Private-email GitHub accounts don't include it on /user - the
        # verified primary address is only on /user/emails (needs user:email scope).
        emails_response = requests.get(EMAILS_URL, headers=auth_header, timeout=REQUEST_TIMEOUT_SECONDS)
        if emails_response.ok:
            email = _primary_verified_email(emails_response.json())

    if not email:
        raise InvalidGitHubCode("This GitHub account has no verified email address to sign in with.")

    return {"email": email, "name": profile.get("name") or profile.get("login", "")}


def get_or_create_user_from_github(email: str, name: str):
    return get_or_create_oauth_user(email, name)
