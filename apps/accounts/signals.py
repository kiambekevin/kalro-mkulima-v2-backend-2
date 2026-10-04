# apps/accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, Profile


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Every new user gets a Profile automatically."""
    if created:
        Profile.objects.get_or_create(user=instance)