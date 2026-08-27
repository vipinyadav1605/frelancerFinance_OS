"""
Sequential invoice numbering (FR-5, PRD NFR: "no gaps or reuse").

Uses select_for_update inside an atomic transaction so two concurrent
invoice creations for the same business can never be assigned the same
number, even under concurrent requests.
"""

from django.db import transaction

from accounts.models import BusinessProfile


def next_invoice_number(user) -> str:
    with transaction.atomic():
        profile = BusinessProfile.objects.select_for_update().get(user=user)
        sequence = profile.next_invoice_sequence
        profile.next_invoice_sequence = sequence + 1
        profile.save(update_fields=["next_invoice_sequence"])

    return f"{profile.invoice_prefix}-{sequence:05d}"
