"""
Phase 5: fires outgoing webhooks for third-party integrations.

Delivery is best-effort and synchronous (no Celery/Redis in this project yet
- matches the "cron first, background worker later" approach used elsewhere).
A slow or broken subscriber endpoint should never block the request that
triggered the event, so every failure is caught and logged as a
WebhookDelivery row rather than raised.
"""

import hashlib
import hmac
import json
import logging

import requests

from .. import models
from .url_safety import UnsafeWebhookUrlError, assert_safe_webhook_url

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_webhook_event(user, event: str, payload: dict):
    subscriptions = models.WebhookSubscription.objects.filter(user=user, event=event, is_active=True)
    for subscription in subscriptions:
        body = json.dumps(payload).encode()
        signature = _sign(subscription.secret, body)
        delivery = models.WebhookDelivery(subscription=subscription, event=event, payload=payload)
        try:
            # Re-checked here, not just at subscription creation, in case the
            # hostname's DNS now resolves somewhere it didn't before ("DNS
            # rebinding") - see url_safety.py's module docstring.
            assert_safe_webhook_url(subscription.url)
            response = requests.post(
                subscription.url,
                data=body,
                headers={"Content-Type": "application/json", "X-Ffos-Signature": signature},
                timeout=TIMEOUT_SECONDS,
            )
            delivery.status_code = response.status_code
            delivery.success = response.ok
            if not response.ok:
                delivery.error_message = f"Non-2xx response: {response.status_code}"
        except (requests.RequestException, UnsafeWebhookUrlError) as exc:
            delivery.success = False
            delivery.error_message = str(exc)[:255]
            logger.warning("Webhook delivery failed for %s (%s): %s", subscription.url, event, exc)
        delivery.save()
