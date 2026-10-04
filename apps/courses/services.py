# apps/courses/services.py
"""
Authoring and publishing workflow. Called from management commands,
Celery tasks, and admin actions.
"""
import logging

from django.db import transaction
from django.utils import timezone

from .constants import MIN_LESSONS_PER_COURSE, MAX_LESSONS_PER_COURSE
from .models import Course, Module, Lesson, Resource

logger = logging.getLogger(__name__)


# ───────────────────────────── Publish ─────────────────────────────

class PublishError(Exception):
    """Raised when a course is not ready to publish."""


@transaction.atomic
def publish_course(course: Course) -> Course:
    """
    Validate the course is ready, then flip `is_published = True`.

    Rules:
      - Must have at least MIN_LESSONS_PER_COURSE lessons.
      - Must have at most MAX_LESSONS_PER_COURSE lessons.
      - Every video lesson must have a stream_url.
      - Every resource lesson must have a file or URL.
    """
    lessons = list(
        Lesson.objects.filter(module__course=course).order_by("module__order", "order")
    )

    if len(lessons) < MIN_LESSONS_PER_COURSE:
        raise PublishError(
            f"Course needs at least {MIN_LESSONS_PER_COURSE} lessons "
            f"(currently {len(lessons)})."
        )

    if len(lessons) > MAX_LESSONS_PER_COURSE:
        raise PublishError(
            f"Course has {len(lessons)} lessons — the maximum is "
            f"{MAX_LESSONS_PER_COURSE}."
        )

    for lesson in lessons:
        if lesson.type == Lesson.Type.VIDEO and not lesson.stream_url:
            raise PublishError(
                f"Video lesson '{lesson.title}' has no stream URL."
            )
        if lesson.type == Lesson.Type.RESOURCE and not (lesson.resource_file or lesson.resource_label):
            raise PublishError(
                f"Resource lesson '{lesson.title}' has no file or label."
            )

    course.is_published = True
    course.published_at = course.published_at or timezone.now()
    course.save(update_fields=["is_published", "published_at", "updated_at"])

    logger.info("Published course %s (%d lessons).", course.slug, len(lessons))
    return course


@transaction.atomic
def unpublish_course(course: Course) -> Course:
    course.is_published = False
    course.save(update_fields=["is_published", "updated_at"])
    logger.info("Unpublished course %s.", course.slug)
    return course


# ───────────────────────────── Bulk import ─────────────────────────────

@transaction.atomic
def import_course_from_dict(payload: dict) -> Course:
    """
    Create (or replace) a course from a JSON structure matching
    src/data/courses.js. Used by the seeding command and content import
    from KALRO's internal content tools.
    """
    from .models import Subject

    subject_slug = payload["subject"]
    subject, _ = Subject.objects.get_or_create(
        slug=subject_slug,
        defaults={"label": payload.get("subjectLabel", subject_slug.title())},
    )

    course, created = Course.objects.update_or_create(
        slug=payload["slug"],
        defaults={
            "title": payload["title"],
            "summary": payload["summary"],
            "subject": subject,
            "level": payload["level"],
            "hours": payload.get("hours", 1),
            "rating": payload.get("rating", 0),
            "review_count": payload.get("reviewCount", 0),
            "badge_enabled": payload.get("badge", True),
            "popular": payload.get("popular", False),
            "image": payload.get("image", ""),
            "alt_text": payload.get("alt", ""),
            "is_published": True,
        },
    )

    curriculum = payload.get("curriculum") or []
    if curriculum:
        # Replace modules wholesale on import
        course.modules.all().delete()

        for mi, module_data in enumerate(curriculum, start=1):
            module = Module.objects.create(
                course=course,
                title=module_data["title"],
                order=mi,
            )
            for li, lesson_data in enumerate(module_data.get("lessons", []), start=1):
                lesson = Lesson.objects.create(
                    module=module,
                    slug=lesson_data.get("id") or f"m{mi}l{li}",
                    title=lesson_data["title"],
                    body=lesson_data.get("body", ""),
                    type=lesson_data.get("type", Lesson.Type.READING),
                    minutes=lesson_data.get("minutes", 10),
                    order=li,
                    is_preview=lesson_data.get("preview", False),
                    stream_url=lesson_data.get("streamUrl", ""),
                    poster_url=lesson_data.get("poster", ""),
                    resource_label=lesson_data.get("resourceLabel", ""),
                    notes=lesson_data.get("notes", []),
                )

                for ri, res in enumerate(lesson_data.get("resources", []), start=1):
                    Resource.objects.create(
                        lesson=lesson,
                        kind=res.get("type", "link"),
                        title=res["title"],
                        publisher=res.get("publisher", ""),
                        description=res.get("description", ""),
                        url=res.get("url", ""),
                        size_label=res.get("size", ""),
                        category=res.get("category", ""),
                        order=ri,
                    )

    return course


# ───────────────────────────── Stats ─────────────────────────────

def refresh_course_stats(course: Course) -> Course:
    """
    Recalculate aggregate stats (lesson count, hours) from the
    curriculum. Called after any module/lesson change.
    """
    lessons = Lesson.objects.filter(module__course=course)
    total_minutes = sum(lessons.values_list("minutes", flat=True))
    course.hours = max(1, round(total_minutes / 60))
    course.save(update_fields=["hours", "updated_at"])
    return course