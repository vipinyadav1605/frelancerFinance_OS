"""
Backfills default expense categories for users created before this app
existed (e.g. anyone who signed up during Phase 1). New users get theirs via
the post_save signal in signals.py - this migration only covers the gap.
"""

from django.db import migrations

from expenses.constants import DEFAULT_EXPENSE_CATEGORIES


def seed_categories(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    ExpenseCategory = apps.get_model("expenses", "ExpenseCategory")

    for user in User.objects.all():
        existing_names = set(
            ExpenseCategory.objects.filter(user=user).values_list("name", flat=True)
        )
        ExpenseCategory.objects.bulk_create([
            ExpenseCategory(user=user, name=name, is_default=True)
            for name in DEFAULT_EXPENSE_CATEGORIES
            if name not in existing_names
        ])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, noop_reverse),
    ]
