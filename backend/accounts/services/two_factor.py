import base64
import io

import pyotp
import qrcode

from ..models import TwoFactorAuth

ISSUER_NAME = "Freelancer Finance OS"


def start_setup(user) -> dict:
    """(Re)generates a pending (not-yet-enabled) secret and returns it plus a scannable QR code."""
    secret = pyotp.random_base32()
    TwoFactorAuth.objects.update_or_create(user=user, defaults={"secret": secret, "is_enabled": False})

    otpauth_uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER_NAME)

    qr = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    return {"secret": secret, "otpauth_uri": otpauth_uri, "qr_code_data_uri": qr_data_uri}


def confirm_setup(user, code: str) -> bool:
    tfa = TwoFactorAuth.objects.filter(user=user).first()
    if tfa is None or tfa.is_enabled:
        return False
    if not pyotp.TOTP(tfa.secret).verify(code, valid_window=1):
        return False
    tfa.is_enabled = True
    tfa.save(update_fields=["is_enabled"])
    return True


def verify_code(user, code: str) -> bool:
    tfa = getattr(user, "two_factor_auth", None)
    if tfa is None or not tfa.is_enabled:
        return False
    return pyotp.TOTP(tfa.secret).verify(code, valid_window=1)


def is_enabled(user) -> bool:
    tfa = getattr(user, "two_factor_auth", None)
    return tfa is not None and tfa.is_enabled


def disable(user) -> None:
    TwoFactorAuth.objects.filter(user=user).delete()
