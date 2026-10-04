# apps/progress/services.py
"""
Business logic for marking lessons complete / incomplete, keeping
CourseProgress in sync, and firing badge issuance.
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.courses.models import Course, Lesson
from .constants import COMPLETION_THRESHOLD
from .models import CourseProgress, DailyActivity, LessonCompletion
from .selectors import recompute_daily_activity

logger = logging.getLogger(__name__)


# ───────────────────────────── Exceptions ─────────────────────────────

class ProgressError(Exception):
    """Raised when a progress mutation can't be performed."""


# ───────────────────────────── Complete ─────────────────────────────

@transaction.atomic
def complete_lesson(user, lesson: Lesson, *, minutes_spent: int = 0) -> CourseProgress:
    """
    Marks a lesson complete for a user, updates the CourseProgress
    rollup, refreshes today's activity, and signals badge issuance if
    the course is now finished.

    Idempotent — calling twice has no extra effect.
    """
    course = lesson.module.course
    now = timezone.now()

    completion, created = LessonCompletion.objects.get_or_create(
        user=user, lesson=lesson,
        defaults={"course": course, "completed_at": now},
    )

    if not created:
        # Nothing new — still ensure the rollup is coherent
        cp = _ensure_course_progress(user, course)
        cp.recalculate()
        return cp

    # Update rollups
    cp = _ensure_course_progress(user, course)
    cp.last_lesson = lesson
    cp.last_seen_at = now
    cp.save(update_fields=["last_lesson", "last_seen_at", "updated_at"])
    cp.recalculate()

    # Daily activity
    recompute_daily_activity(user, target_date=timezone.localdate())

    # If the course is complete, issue the badge (fires via signal too,
    # but calling it explicitly is clearer for tests and admin scripts).
    if cp.percent >= COMPLETION_THRESHOLD:
        try:
            from apps.badges.services import issue_badge
            issue_badge(user, course)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to issue badge after completing course %s", course.slug)

    logger.info(
        "Lesson completed: user=%s lesson=%s course=%s (%d%%)",
        user.id, lesson.slug, course.slug, cp.percent,
    )
    return cp


# ───────────────────────────── Uncomplete ─────────────────────────────

@transaction.atomic
def uncomplete_lesson(user, lesson: Lesson) -> CourseProgress:
    """
    Removes a completion. Also removes the badge if the course is no
    longer complete (rare case, but keeps data honest).
    """
    course = lesson.module.course

    LessonCompletion.objects.filter(user=user, lesson=lesson).delete()

    cp = _ensure_course_progress(user, course)
    cp.recalculate()

    recompute_daily_activity(user, target_date=timezone.localdate())

    if cp.percent < COMPLETION_THRESHOLD:
        from apps.badges.models import Badge
        Badge.objects.filter(
            user=user, course=course, status=Badge.Status.ISSUED,
        ).update(status=Badge.Status.REVOKED, revoked_at=timezone.now())

    logger.info(
        "Lesson uncompleted: user=%s lesson=%s course=%s (%d%%)",
        user.id, lesson.slug, course.slug, cp.percent,
    )
    return cp


# ───────────────────────────── Toggle ─────────────────────────────

def toggle_lesson(user, lesson: Lesson, *, force: bool = False) -> tuple[CourseProgress, bool]:
    """
    Convenience for the UI toggle. Returns (course_progress, is_completed_now).
    """
    exists = LessonCompletion.objects.filter(user=user, lesson=lesson).exists()
    if force or not exists:
        return complete_lesson(user, lesson), True
    return uncomplete_lesson(user, lesson), False


# ───────────────────────────── Last lesson ─────────────────────────────

@transaction.atomic
def set_last_lesson(user, course: Course, lesson: Lesson) -> CourseProgress:
    """
    Called by the lesson viewer every time a lesson loads. Powers the
    'Resume' button on the dashboard.
    """
    cp = _ensure_course_progress(user, course)
    cp.last_lesson = lesson
    cp.last_seen_at = timezone.now()
    cp.save(update_fields=["last_lesson", "last_seen_at", "updated_at"])
    return cp


# ───────────────────────────── Rebuild ─────────────────────────────

@transaction.atomic
def rebuild_course_progress(user, course) -> CourseProgress:
    """
    Recomputes CourseProgress from scratch. Used by the management
    command and when a course's curriculum changes.
    """
    cp = _ensure_course_progress(user, course)
    cp.recalculate()
    return cp


def rebuild_user_progress(user) -> int:
    """
    Rebuilds CourseProgress for every course the user has touched.
    """
    course_ids = (
        LessonCompletion.objects
        .filter(user=user)
        .values_list("course_id", flat=True)
        .distinct()
    )
    count = 0
    for cid in course_ids:
        course = Course.objects.filter(id=cid).first()
        if not course:
            continue
        rebuild_course_progress(user, course)
        count += 1
    return count


# ───────────────────────────── Helpers ─────────────────────────────

def _ensure_course_progress(user, course) -> CourseProgress:
    cp, _ = CourseProgress.objects.get_or_create(user=user, course=course)
    return cp