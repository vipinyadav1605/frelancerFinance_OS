from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .constants import DEFAULT_EXPENSE_CATEGORIES
from .models import ExpenseCategory


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def seed_default_expense_categories(sender, instance, created, **kwargs):
    """Every new user gets the default category set (PRD Phase 2 feature list)."""
    if not created:
        return
    ExpenseCategory.objects.bulk_create(
        [ExpenseCategory(user=instance, name=name, is_default=True) for name in DEFAULT_EXPENSE_CATEGORIES]
    )
