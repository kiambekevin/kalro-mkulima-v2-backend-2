# apps/common/managers.py
from django.db import models


class ActiveManager(models.Manager):
    """
    Returns only `is_active=True` rows. Used by models that don't want
    a full soft-delete scheme but still want a simple active flag.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SoftDeleteManager(models.Manager):
    """
    Default manager for SoftDeleteModel — hides deleted rows. Use
    `Model.objects_all` (declared alongside) to see everything.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, deleted_at__isnull=True)


class PublishedManager(models.Manager):
    """
    Returns only published rows. Assumes the model has both
    `is_published` and (optionally) `published_at`.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)