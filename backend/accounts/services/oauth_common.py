"""Shared "find or create a user from a verified OAuth profile" logic, used
by google_auth.py, microsoft_auth.py, and github_auth.py alike - each
provider only differs in how it verifies a token/code into {email, name}."""

from ..models import User


def get_or_create_oauth_user(email: str, name: str) -> User:
    # Deliberately not get_or_create(email__iexact=...) - that lookup kwarg
    # would also get passed straight through to create(), which doesn't
    # accept an "email__iexact" field.
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create(email=email, name=name)
        user.set_unusable_password()  # this account can only ever sign in via an OAuth provider
        user.save(update_fields=["password"])
    return user
