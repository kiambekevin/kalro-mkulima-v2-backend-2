# apps/progress/selectors.py
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.courses.models import Lesson, Course
from .constants import MIN_LESSONS_FOR_STREAK_DAY, ACTIVITY_REBUILD_DAYS
from .models import CourseProgress, LessonCompletion, DailyActivity


# ───────────────────────────── Progress ─────────────────────────────

def progress_for_course(user, course) -> CourseProgress | None:
    return (
        CourseProgress.objects
        .filter(user=user, course=course)
        .select_related("course", "last_lesson")
        .first()
    )


def all_progress_for_user(user):
    return (
        CourseProgress.objects
        .for_user(user)
        .with_course()
        .recent_first()
    )


def completed_lesson_ids(user, course) -> set:
    return set(
        LessonCompletion.objects
        .filter(user=user, course=course)
        .values_list("lesson_id", flat=True)
    )


def resume_lesson(user, course):
    """
    Returns the lesson a learner should resume, or the first lesson in
    the course if they haven't started.
    """
    cp = progress_for_course(user, course)
    if cp and cp.last_lesson and not cp.last_lesson.completions.filter(user=user).exists():
        return cp.last_lesson

    # Otherwise, find the first uncompleted lesson in order
    completed = completed_lesson_ids(user, course)
    ordered = (
        Lesson.objects
        .filter(module__course=course)
        .order_by("module__order", "order")
        .values("id", "slug", "title", "minutes")
    )
    for row in ordered:
        if row["id"] not in completed:
            return row
    return None  # Course fully completed


# ───────────────────────────── Activity ─────────────────────────────

def activity_for_range(user, start, end):
    return (
        DailyActivity.objects
        .for_user(user)
        .between(start, end)
        .order_by("date")
    )


def activity_last_n_days(user, n: int = 7):
    return (
        DailyActivity.objects
        .for_user(user)
        .last_n_days(n)
        .order_by("date")
    )


def recompute_daily_activity(user, target_date=None) -> DailyActivity:
    """
    Counts today's (or a given day's) LessonCompletion rows and
    refreshes the DailyActivity rollup.
    """
    target_date = target_date or timezone.localdate()
    day_start = timezone.make_aware(
        timezone.datetime.combine(target_date, timezone.datetime.min.time()),
        timezone.get_current_timezone(),
    )
    day_end = day_start + timedelta(days=1)

    rows = LessonCompletion.objects.filter(
        user=user, completed_at__gte=day_start, completed_at__lt=day_end,
    )
    lessons = rows.count()
    minutes = sum(rows.values_list("lesson__minutes", flat=True))
    distinct_courses = rows.values("course_id").distinct().count()

    activity, _ = DailyActivity.objects.update_or_create(
        user=user, date=target_date,
        defaults={
            "lessons_completed": lessons,
            "minutes_spent": minutes or 0,
            "courses_touched": distinct_courses,
        },
    )
    return activity


# ───────────────────────────── Streaks ─────────────────────────────

def current_streak(user) -> int:
    """
    Consecutive days with at least MIN_LESSONS_FOR_STREAK_DAY lessons
    completed, ending today or yesterday.
    """
    today = timezone.localdate()
    active_days = set(
        DailyActivity.objects
        .filter(user=user, lessons_completed__gte=MIN_LESSONS_FOR_STREAK_DAY)
        .values_list("date", flat=True)
    )

    if not active_days:
        return 0

    cursor = today
    if cursor not in active_days:
        cursor = today - timedelta(days=1)
        if cursor not in active_days:
            return 0

    streak = 0
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def longest_streak(user) -> int:
    """
    Longest consecutive run of active days in the user's history.
    """
    dates = list(
        DailyActivity.objects
        .filter(user=user, lessons_completed__gte=MIN_LESSONS_FOR_STREAK_DAY)
        .order_by("date")
        .values_list("date", flat=True)
    )
    if not dates:
        return 0

    longest = 1
    current = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def is_active_today(user) -> bool:
    today = timezone.localdate()
    return DailyActivity.objects.filter(
        user=user, date=today,
        lessons_completed__gte=MIN_LESSONS_FOR_STREAK_DAY,
    ).exists()