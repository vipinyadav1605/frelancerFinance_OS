"""Backfills a unique referral_code for users created before this field existed."""

import secrets

from django.db import migrations


def backfill_codes(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(referral_code__isnull=True):
        user.referral_code = secrets.token_urlsafe(6)
        user.save(update_fields=["referral_code"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_user_referral_code_user_referred_by"),
    ]

    operations = [
        migrations.RunPython(backfill_codes, noop_reverse),
    ]
