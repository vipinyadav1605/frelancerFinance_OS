"""
Live exchange-rate lookup for multi-currency invoices (Phase 4 "polish").

This only suggests a rate - the user can always override it manually on the
invoice form, since the rate actually used for a past invoice must stay
whatever was true (or agreed with the client) on that day, not whatever the
API returns when someone looks it up later.
"""

from decimal import Decimal

import requests
from django.core.cache import cache

EXCHANGE_RATE_API_URL = "https://open.er-api.com/v6/latest/{base}"
CACHE_TIMEOUT_SECONDS = 6 * 60 * 60


def fetch_exchange_rate_to_inr(currency_code: str) -> Decimal:
    if currency_code == "INR":
        return Decimal("1")

    cache_key = f"fx_rate_to_inr_{currency_code}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Decimal(cached)

    response = requests.get(EXCHANGE_RATE_API_URL.format(base=currency_code), timeout=5)
    response.raise_for_status()
    payload = response.json()
    rate = Decimal(str(payload["rates"]["INR"])).quantize(Decimal("0.0001"))

    cache.set(cache_key, str(rate), CACHE_TIMEOUT_SECONDS)
    return rate
