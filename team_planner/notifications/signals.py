"""
Django signals for automatic notification triggers.

These signals listen for model changes and automatically send notifications.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import NotificationPreference

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Automatically create notification preferences when a user is created."""
    if created:
        NotificationPreference.objects.get_or_create(user=instance)
