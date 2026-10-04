# apps/common/models.py
"""
Shared abstract base models.

Every domain model in the project should inherit from one of these
instead of `models.Model` directly. That gives every row a consistent
`created_at`/`updated_at` pair, an optional UUID PK, and a soft-delete
mechanism.

None of these classes create a table of their own — they're abstract.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .managers import ActiveManager, SoftDeleteManager


class TimeStampedModel(models.Model):
    """
    Adds `created_at` and `updated_at` to any model.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class UUIDModel(models.Model):
    """
    Primary key as a UUID v4. Safer to expose in URLs than integer IDs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SluggedModel(models.Model):
    """
    Ensures the model has a `slug` and auto-populates it from a
    configurable source field on first save.

    Subclasses should set `slug_source_field = "title"` (default).
    """
    slug_source_field = "title"
    slug_max_length = 80

    slug = models.SlugField(
        max_length=120, unique=True, db_index=True, blank=True,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            source = getattr(self, self.slug_source_field, "") or ""
            from .utils import unique_slug
            self.slug = unique_slug(self, source, max_length=self.slug_max_length)
        super().save(*args, **kwargs)


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self):
        return self.update(is_active=False, deleted_at=timezone.now())

    def restore(self):
        return self.update(is_active=True, deleted_at=None)


class SoftDeleteModel(models.Model):
    """
    Rows are never hard-deleted from the database. Instead they're
    flagged `is_active=False` and stamped with `deleted_at`.

    QuerySets support `.active()` / `.deleted()` / `.soft_delete()` /
    `.restore()`, and the `objects` manager returns active rows by
    default. Use `objects_all` to bypass the filter.
    """
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    objects_all = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, *, hard=False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_active", "deleted_at", "updated_at"])

    def restore(self):
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=["is_active", "deleted_at", "updated_at"])


class PublishableModel(models.Model):
    """
    Adds a `is_published` flag and a `published_at` timestamp.
    Subclasses can override `publish()` to add validation.
    """
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def publish(self, save=True):
        self.is_published = True
        self.published_at = self.published_at or timezone.now()
        if save:
            self.save(update_fields=["is_published", "published_at", "updated_at"])
        return self

    def unpublish(self, save=True):
        self.is_published = False
        if save:
            self.save(update_fields=["is_published", "updated_at"])
        return self


class AuditLogModel(models.Model):
    """
    Optional mixin that records who created and last updated a row.
    Consumers must add `created_by` and `updated_by` FKs themselves —
    the mixin only declares the columns so apps stay decoupled.
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True