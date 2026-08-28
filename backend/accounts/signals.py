from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import NotificationPreference


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def seed_notification_preference(sender, instance, created, **kwargs):
    """Every new user gets a default (all-on) notification preference row."""
    if not created:
        return
    NotificationPreference.objects.create(user=instance)
