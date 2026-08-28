"""Backfills a unique public_view_token for invoices created before this field existed."""

import secrets

from django.db import migrations


def backfill_tokens(apps, schema_editor):
    Invoice = apps.get_model("invoicing", "Invoice")
    for invoice in Invoice.objects.filter(public_view_token__isnull=True):
        invoice.public_view_token = secrets.token_urlsafe(24)
        invoice.save(update_fields=["public_view_token"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("invoicing", "0004_invoice_public_view_token_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_tokens, noop_reverse),
    ]
