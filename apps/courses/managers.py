# apps/courses/managers.py
from django.db import models


class SubjectQuerySet(models.QuerySet):
    def with_course_counts(self):
        return self.annotate(
            course_count=models.Count(
                "courses",
                filter=models.Q(courses__is_published=True),
            )
        )


class SubjectManager(models.Manager.from_queryset(SubjectQuerySet)):
    pass


class CourseQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def popular(self):
        return self.filter(popular=True, is_published=True).order_by("-rating")

    def by_subject(self, slug):
        return self.filter(subject__slug=slug)

    def with_curriculum(self):
        """Prefetch modules, lessons and resources in three queries."""
        return self.prefetch_related(
            "modules",
            "modules__lessons",
            "modules__lessons__resources",
        )

    def with_instructor(self):
        return self.select_related("instructor", "subject")


class CourseManager(models.Manager.from_queryset(CourseQuerySet)):
    pass


class LessonQuerySet(models.QuerySet):
    def with_resources(self):
        return self.prefetch_related("resources")

    def previews(self):
        return self.filter(is_preview=True)


class LessonManager(models.Manager.from_queryset(LessonQuerySet)):
    pass