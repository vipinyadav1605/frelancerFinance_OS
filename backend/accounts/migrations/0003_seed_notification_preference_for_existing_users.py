"""
Backfills a NotificationPreference row for users created before this feature
existed. New users get theirs via the post_save signal in signals.py - this
migration only covers the gap (same pattern as expenses/migrations/0002).
"""

from django.db import migrations


def seed_preferences(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    NotificationPreference = apps.get_model("accounts", "NotificationPreference")

    existing_user_ids = set(NotificationPreference.objects.values_list("user_id", flat=True))
    NotificationPreference.objects.bulk_create([
        NotificationPreference(user=user)
        for user in User.objects.exclude(pk__in=existing_user_ids)
    ])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_businessprofile_email_signoff_notificationpreference"),
    ]

    operations = [
        migrations.RunPython(seed_preferences, noop_reverse),
    ]
