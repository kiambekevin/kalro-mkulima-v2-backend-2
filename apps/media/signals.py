# apps/media/signals.py
"""
Housekeeping signals for media assets:
  - auto-slug when missing
  - clean up orphan files when an asset is deleted
  - clear cached signed URLs when an asset changes
"""
import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from .models import MediaAsset

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=MediaAsset)
def ensure_slug(sender, instance, **kwargs):
    if not instance.slug and instance.title:
        instance.slug = slugify(instance.title)[:120]


@receiver(post_delete, sender=MediaAsset)
def delete_file_on_asset_delete(sender, instance, **kwargs):
    """Delete the stored file when the asset row is removed."""
    if instance.file:
        try:
            instance.file.delete(save=False)
        except Exception:  # noqa: BLE001
            logger.warning("Could not delete file for asset %s", instance.slug)

    cache.delete(f"media:signed:{instance.id}")