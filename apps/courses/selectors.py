# apps/courses/selectors.py
"""
Read-only query functions for the courses app.

Views, serializers and other apps should call functions from here
rather than querying models directly. This keeps query optimisation
in one place and makes it easy to see every "hot path" in the
catalogue at a glance.
"""
import uuid as uuid_lib

from django.db.models import Count, Prefetch, Q

from .models import Course, Lesson, Module, Pathway, PathwayCourse, Resource, Subject


# ───────────────────────────── Subjects ─────────────────────────────

def subjects_with_counts():
    """
    All subjects, annotated with their published course count.

    Used by:
      - the "Explore by subject" grid on the homepage
      - GET /api/v1/subjects/
    """
    return (
        Subject.objects
        .annotate(
            course_count=Count(
                "courses",
                filter=Q(courses__is_published=True),
                distinct=True,
            )
        )
        .order_by("order", "label")
    )


def subject_by_slug(slug: str) -> Subject | None:
    """
    Fetch a single subject by slug, annotated with course_count.
    """
    return (
        Subject.objects
        .annotate(
            course_count=Count(
                "courses",
                filter=Q(courses__is_published=True),
                distinct=True,
            )
        )
        .filter(slug=slug)
        .first()
    )


# ───────────────────────────── Courses (list) ─────────────────────────────

def published_courses():
    """
    Base queryset for the catalogue list. Prefetches the instructor and
    subject so card rendering never triggers extra queries.
    """
    return (
        Course.objects
        .published()
        .with_instructor()
        .order_by("-popular", "-rating", "title")
    )


def popular_courses(limit: int = 6):
    """
    Homepage "Popular courses" strip — the top N by rating among
    courses flagged `popular=True`.
    """
    return Course.objects.popular()[:limit]


# ───────────────────────────── Course (detail) ─────────────────────────────

def course_by_slug(slug: str) -> Course | None:
    """
    Detail-page loader.

    Three queries total regardless of the number of modules/lessons:
      1. the course + instructor + subject
      2. its modules (ordered)
      3. each module's lessons (ordered)
    """
    return (
        Course.objects
        .published()
        .with_instructor()
        .prefetch_related(
            Prefetch(
                "modules",
                queryset=Module.objects.order_by("order").prefetch_related(
                    Prefetch(
                        "lessons",
                        queryset=Lesson.objects.order_by("order"),
                    ),
                ),
            ),
        )
        .filter(slug=slug)
        .first()
    )


def course_curriculum(course: Course):
    """
    Modules with lessons for a given course, ordered. Used by the
    `/curriculum/` action and by the detail serializer.
    """
    return (
        course.modules
        .order_by("order")
        .prefetch_related(
            Prefetch(
                "lessons",
                queryset=Lesson.objects.order_by("order"),
            ),
        )
    )


def related_courses(course: Course, limit: int = 4):
    """
    Courses to show under "More in this subject".

    Prefers same-subject courses; if there are none, falls back to any
    other published course, ranked by popularity then rating.
    """
    base = (
        Course.objects
        .published()
        .exclude(pk=course.pk)
        .order_by("-popular", "-rating")
    )

    same_subject = base.filter(subject=course.subject)[:limit]
    if same_subject.count() >= limit:
        return same_subject

    # Fill the remaining slots with anything else
    exclude_ids = [course.pk] + [c.pk for c in same_subject]
    fallback = base.exclude(pk__in=exclude_ids)[: limit - same_subject.count()]
    return list(same_subject) + list(fallback)


# ───────────────────────────── Lessons ─────────────────────────────

def lesson_by_identifier(course_slug: str, identifier: str) -> Lesson | None:
    """
    Resolve a lesson by EITHER its slug OR its UUID, scoped to a
    specific course.

    Accepts:
      - "m2l1"                                      (slug)
      - "677536f9-c53c-40f1-b89d-2531d8c676db"      (UUID)

    Used by LessonView so URLs from any frontend version resolve
    correctly regardless of which identifier they carry.
    """
    base = (
        Lesson.objects
        .filter(module__course__slug=course_slug)
        .select_related("module", "module__course", "module__course__subject")
        .prefetch_related("resources")
    )

    # Try UUID first — unambiguous and cheap
    try:
        as_uuid = uuid_lib.UUID(str(identifier))
        hit = base.filter(id=as_uuid).first()
        if hit:
            return hit
    except (ValueError, TypeError, AttributeError):
        pass

    # Fall back to slug match (case-insensitive)
    return base.filter(slug__iexact=str(identifier)).first()


def lessons_for_course(course: Course):
    """
    Ordered flat list of lessons in a course. Used by progress
    recalculations and by the completion signal to count totals.
    """
    return (
        Lesson.objects
        .filter(module__course=course)
        .order_by("module__order", "order")
    )


def lesson_count_for_course(course: Course) -> int:
    """
    Number of lessons in a course. One aggregate query.
    """
    return Lesson.objects.filter(module__course=course).count()


# ───────────────────────────── Resources ─────────────────────────────

def course_resources(course: Course):
    """
    Every resource attached to any lesson in the course, ordered by
    module → lesson → resource order. Used by
    `GET /courses/{slug}/resources/`.
    """
    return (
        Resource.objects
        .filter(lesson__module__course=course)
        .select_related("lesson")
        .order_by(
            "lesson__module__order",
            "lesson__order",
            "order",
        )
    )


def resources_for_lesson(lesson: Lesson):
    """
    Ordered resources attached to a single lesson. Used by the lesson
    serializer when it emits nested resources.
    """
    return lesson.resources.order_by("order")



# apps/courses/selectors.py — append

def published_pathways():
    return (
        Pathway.objects
        .filter(is_published=True)
        .prefetch_related(
            Prefetch(
                "pathway_courses",
                queryset=PathwayCourse.objects
                    .select_related("course")
                    .order_by("order"),
            ),
        )
        .order_by("order", "title")
    )


def pathway_by_slug(slug: str):
    return (
        Pathway.objects
        .filter(is_published=True, slug=slug)
        .prefetch_related(
            Prefetch(
                "pathway_courses",
                queryset=PathwayCourse.objects
                    .select_related("course")
                    .order_by("order"),
            ),
        )
        .first()
    )