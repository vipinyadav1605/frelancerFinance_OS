"""
Razorpay integration (FR-6): payment link creation and webhook verification.

NOTE (important limitation to know before going live): Razorpay Payment
Links are issued in INR by default; accepting a foreign-currency invoice
via a simple payment link means charging the client the INR equivalent
(using the exchange rate captured on the invoice) unless/until an
international payments setup is arranged with Razorpay. That is the
assumption implemented below - flagged here so it isn't a silent surprise.
"""

import razorpay
from django.conf import settings


def _client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_payment_link(invoice) -> dict:
    """Creates a Razorpay payment link for the invoice's INR-equivalent amount."""
    amount_inr = invoice.total_amount * invoice.exchange_rate_to_inr
    amount_paise = int(round(amount_inr * 100))

    link = _client().payment_link.create({
        "amount": amount_paise,
        "currency": "INR",
        "description": f"Invoice {invoice.invoice_number}",
        "customer": {
            "name": invoice.client_name_snapshot,
            "email": invoice.client_email_snapshot or None,
        },
        "notify": {"email": bool(invoice.client_email_snapshot)},
        "reference_id": invoice.invoice_number,
    })
    return {"id": link["id"], "short_url": link["short_url"]}


def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    try:
        _client().utility.verify_webhook_signature(
            payload_body.decode("utf-8"), signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
