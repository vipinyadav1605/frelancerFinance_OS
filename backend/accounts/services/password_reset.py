"""
Password reset via a signed, expiring link - the standard Django pattern
(same token generator used by the admin site's own reset flow), adapted to
email a link into the SPA frontend instead of rendering a Django template.

The token is a hash of the user's pk, password hash, and last_login,
timestamped and signed with SECRET_KEY - so it can't be forged, and it stops
working the moment the password actually changes (the hash it was built
from no longer matches) or after PASSWORD_RESET_TIMEOUT (Django default: 3
days). No separate token storage/expiry table needed.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from ..models import User


def send_password_reset_email(email: str) -> None:
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        return  # Deliberately silent - the API response must not reveal whether an email is registered.

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password/{uid}/{token}/"

    EmailMessage(
        subject="Reset your Freelancer Finance OS password",
        body=(
            f"Hi {user.name or user.email},\n\n"
            f"Click the link below to reset your password. This link expires in a few days "
            f"and can only be used once.\n\n{reset_url}\n\n"
            "If you didn't request this, you can safely ignore this email."
        ),
        to=[user.email],
    ).send(fail_silently=False)


def reset_password_with_token(*, uid: str, token: str, new_password: str) -> bool:
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return False

    if not default_token_generator.check_token(user, token):
        return False

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True
