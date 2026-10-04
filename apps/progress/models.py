# apps/progress/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from .managers import (
    CourseProgressManager,
    DailyActivityManager,
    LessonCompletionManager,
)


class CourseProgress(TimeStampedModel):
    """
    One row per (user, course). Keeps a denormalised count and percent
    so the dashboard can sort and filter without aggregating over every
    LessonCompletion.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_progress",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="progress",
    )

    last_lesson = models.ForeignKey(
        "courses.Lesson",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Used for the 'Resume' button on the dashboard.",
    )
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)

    completed_count = models.PositiveIntegerField(default=0, db_index=True)
    total_count = models.PositiveIntegerField(default=0)
    percent = models.PositiveSmallIntegerField(default=0, db_index=True)

    objects = CourseProgressManager()

    class Meta:
        ordering = ["-last_seen_at", "-updated_at"]
        unique_together = [("user", "course")]
        indexes = [
            models.Index(fields=["user", "percent"]),
            models.Index(fields=["user", "-last_seen_at"]),
            models.Index(fields=["course", "percent"]),
        ]
        verbose_name = "Course progress"
        verbose_name_plural = "Course progress records"

    def __str__(self):
        return f"{self.user} · {self.course.slug} · {self.percent}%"

    @property
    def is_complete(self) -> bool:
        return self.percent >= 100

    def recalculate(self, *, save: bool = True) -> "CourseProgress":
        """
        Recompute `completed_count`, `total_count` and `percent` from
        the LessonCompletion table. Cheap: two aggregate queries.
        """
        from apps.courses.models import Lesson

        total = Lesson.objects.filter(module__course=self.course).count()
        done = LessonCompletion.objects.filter(
            user=self.user, course=self.course,
        ).count()

        self.total_count = total
        self.completed_count = done
        self.percent = int((done / total) * 100) if total else 0

        if save:
            self.save(update_fields=[
                "completed_count", "total_count", "percent", "updated_at",
            ])
        return self


class LessonCompletion(TimeStampedModel):
    """
    A single lesson marked complete by a user. Unique on (user, lesson),
    so toggling the same lesson repeatedly is idempotent.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_completions",
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="completions",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="lesson_completions",
    )
    completed_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = LessonCompletionManager()

    class Meta:
        ordering = ["-completed_at"]
        unique_together = [("user", "lesson")]
        indexes = [
            models.Index(fields=["user", "course"]),
            models.Index(fields=["user", "-completed_at"]),
        ]
        verbose_name = "Lesson completion"
        verbose_name_plural = "Lesson completions"

    def __str__(self):
        return f"{self.user} ✓ {self.lesson.title}"


class DailyActivity(models.Model):
    """
    Per-user, per-day rollup. Powers the dashboard's weekly activity
    chart and streak calculation without scanning LessonCompletion
    every request.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_activity",
    )
    date = models.DateField(db_index=True)
    lessons_completed = models.PositiveSmallIntegerField(default=0)
    minutes_spent = models.PositiveIntegerField(default=0)
    courses_touched = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DailyActivityManager()

    class Meta:
        ordering = ["-date"]
        unique_together = [("user", "date")]
        indexes = [
            models.Index(fields=["user", "-date"]),
        ]
        verbose_name = "Daily activity"
        verbose_name_plural = "Daily activity"

    def __str__(self):
        return f"{self.user} · {self.date} · {self.lessons_completed} lessons"