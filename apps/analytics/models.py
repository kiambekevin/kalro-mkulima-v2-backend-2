# apps/analytics/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class VisitEvent(models.Model):
    """
    One row per page-view-style event. Append-only, never updated.

    Records three axes:
      - who      → user (nullable for anonymous), session_id
      - what     → course (FK) and/or lesson (FK), plus a resource_type
      - where    → county (FK, denormalised from the user's profile)
      - when     → created_at (indexed)
    """

    class ResourceType(models.TextChoices):
        COURSE  = "course",  "Course"
        LESSON  = "lesson",  "Lesson"
        PATHWAY = "pathway", "Pathway"
        BADGE   = "badge",   "Badge"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="visit_events",
    )
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    # What
    resource_type = models.CharField(
        max_length=10, choices=ResourceType.choices, db_index=True,
    )
    course = models.ForeignKey(
        "courses.Course",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="visit_events",
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="visit_events",
    )

    # Where
    county = models.ForeignKey(
        "counties.County",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="visit_events",
    )

    # When
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resource_type", "created_at"]),
            models.Index(fields=["course", "created_at"]),
            models.Index(fields=["lesson", "created_at"]),
            models.Index(fields=["county", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
        verbose_name = "Visit event"
        verbose_name_plural = "Visit events"

    def __str__(self):
        return f"{self.resource_type} · {self.created_at:%Y-%m-%d %H:%M}"


class DailyVisitRollup(models.Model):
    """
    Per-day aggregation, refreshed nightly by a Celery task.
    Keeps dashboard queries O(days × dimensions) instead of scanning
    the full event table.
    """
    date = models.DateField(db_index=True)
    resource_type = models.CharField(max_length=10, db_index=True)

    course = models.ForeignKey(
        "courses.Course", null=True, blank=True,
        on_delete=models.CASCADE, related_name="daily_rollups",
    )
    lesson = models.ForeignKey(
        "courses.Lesson", null=True, blank=True,
        on_delete=models.CASCADE, related_name="daily_rollups",
    )
    county = models.ForeignKey(
        "counties.County", null=True, blank=True,
        on_delete=models.CASCADE, related_name="daily_rollups",
    )

    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [
            ("date", "resource_type", "course", "lesson", "county"),
        ]
        indexes = [
            models.Index(fields=["date", "resource_type"]),
        ]

    def __str__(self):
        return f"{self.date} · {self.resource_type} · {self.count}"