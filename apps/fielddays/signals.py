# apps/fielddays/signals.py
"""
Auto-slug for events, and cleanup of expired waitlist entries.
"""
import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import FieldDay

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=FieldDay)
def ensure_slug(sender, instance, **kwargs):
    if not instance.slug and instance.title:
        from apps.common.utils import unique_slug
        instance.slug = unique_slug(instance, instance.title, max_length=120)