# apps/progress/managers.py
from django.db import models
from django.utils import timezone


class CourseProgressQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def in_progress(self):
        return self.filter(percent__gt=0, percent__lt=100)

    def completed(self):
        return self.filter(percent__gte=100)

    def not_started(self):
        return self.filter(percent=0)

    def with_course(self):
        return self.select_related("course", "course__subject", "last_lesson")

    def recent_first(self):
        return self.order_by("-last_seen_at", "-updated_at")


class CourseProgressManager(models.Manager.from_queryset(CourseProgressQuerySet)):
    pass


class LessonCompletionQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def for_course(self, course):
        return self.filter(course=course)

    def recent_first(self):
        return self.order_by("-completed_at")


class LessonCompletionManager(models.Manager.from_queryset(LessonCompletionQuerySet)):
    pass


class DailyActivityQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def between(self, start, end):
        return self.filter(date__gte=start, date__lte=end)

    def last_n_days(self, n: int = 7):
        today = timezone.localdate()
        return self.filter(date__gte=today - timezone.timedelta(days=n - 1))


class DailyActivityManager(models.Manager.from_queryset(DailyActivityQuerySet)):
    pass