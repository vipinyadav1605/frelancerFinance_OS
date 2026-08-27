"""
SSRF protection for user-supplied webhook URLs (Phase 5 follow-up).

A webhook subscription lets a user tell OUR server to make an HTTP request
to a URL of their choosing. Without this check, that's a textbook SSRF
primitive: someone could point it at http://localhost/admin/, an internal
service on the hosting provider's private network, or a cloud metadata
endpoint (e.g. 169.254.169.254) to read secrets the webhook feature was
never meant to expose.

Checked twice by design: once at subscription-creation time (fast feedback
in the UI) and again immediately before every delivery attempt in
services/webhooks.py (because DNS can change between creation and delivery -
"DNS rebinding" - so a host that resolved safely yesterday could resolve to
an internal IP today).
"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


class UnsafeWebhookUrlError(ValueError):
    pass


def _is_unsafe_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


def assert_safe_webhook_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeWebhookUrlError(f"URL scheme must be http or https, not {parsed.scheme!r}.")
    if not parsed.hostname:
        raise UnsafeWebhookUrlError("URL must include a hostname.")

    try:
        resolved_ips = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, None)}
    except socket.gaierror as exc:
        raise UnsafeWebhookUrlError(f"Could not resolve hostname {parsed.hostname!r}.") from exc

    if any(_is_unsafe_ip(ip) for ip in resolved_ips):
        raise UnsafeWebhookUrlError("This URL resolves to a private/internal address and cannot be used.")
