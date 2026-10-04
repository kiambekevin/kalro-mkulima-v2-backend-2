# apps/dashboard/selectors.py
"""
Query functions that pull the raw data the dashboard serializers need.
Kept separate from views so the same queries can be reused by
management commands, tests and reports.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.badges.models import Badge
from apps.badges.selectors import badges_for_user
from apps.courses.models import Course, Lesson
from apps.fielddays.selectors import upcoming_field_days
from apps.progress.models import CourseProgress, DailyActivity, LessonCompletion

from .constants import (
    ACTIVITY_WINDOW_DAYS,
    MAX_FIELD_DAYS,
    MAX_IN_PROGRESS,
    MAX_RECENT_BADGES,
    MAX_RECOMMENDED,
)


# ───────────────────────────── Helpers ─────────────────────────────

def _safe_file_url(field_file) -> str | None:
    """
    Return the URL for a Django FieldFile, or None.

    Guarantees the return value is a string (or None). Some storage
    backends raise inside `.url`, and a truthy but broken FieldFile can
    leak raw bytes into the JSON encoder if we return the object.
    """
    if not field_file:
        return None
    try:
        url = field_file.url
    except Exception:
        return None
    return url if isinstance(url, str) else None


def _snapshot_get(badge, key: str, default=None):
    """
    Safely read a key from a badge's snapshot JSON. Guards against
    non-dict snapshots (which would happen if a fixture wrote raw bytes
    into the JSONField).
    """
    snap = getattr(badge, "snapshot", None)
    if not isinstance(snap, dict):
        return default
    return snap.get(key) or default


def _dec(value) -> float | None:
    """Coerce a Decimal to a JSON-friendly float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ───────────────────────────── Learner: in-progress ─────────────────────────────

def in_progress_courses(user, limit: int = MAX_IN_PROGRESS):
    """
    Courses the user has started but not yet completed, most recently
    seen first.
    """
    qs = (
        CourseProgress.objects
        .filter(user=user, percent__gt=0, percent__lt=100)
        .select_related("course", "course__subject", "last_lesson")
        .order_by("-last_seen_at", "-updated_at")
    )

    rows = list(qs[:limit])
    if not rows:
        return []

    course_ids = [r.course_id for r in rows]
    totals = dict(
        Lesson.objects
        .filter(module__course_id__in=course_ids)
        .values("module__course_id")
        .annotate(n=Count("id"))
        .values_list("module__course_id", "n")
    )

    return [
        {
            "courseId": str(r.course_id),
            "slug": r.course.slug,
            "title": r.course.title,
            "image": r.course.image_url,               
            "alt": r.course.alt_text,
            "subject": r.course.subject.slug,
            "subjectLabel": r.course.subject.label,
            "level": r.course.level,
            "hours": r.course.hours,
            "done": r.completed_count,
            "total": totals.get(r.course_id, 0),
            "percent": r.percent,
            "lastLessonId": str(r.last_lesson_id) if r.last_lesson_id else None,
            "lastLessonSlug": r.last_lesson.slug if r.last_lesson else None,
            "lastSeenAt": r.last_seen_at,
        }
        for r in rows
    ]


# ───────────────────────────── Learner: completed ─────────────────────────────

def completed_courses(user):
    """
    Courses the user has finished. `CourseProgress.percent == 100` is
    the fastest signal — no need to recount lessons.
    """
    qs = (
        CourseProgress.objects
        .filter(user=user, percent__gte=100)
        .select_related("course", "course__subject")
        .order_by("-updated_at")
    )
    return [
        {
            "courseId": str(p.course_id),
            "slug": p.course.slug,
            "title": p.course.title,
            "subject": p.course.subject.slug,
            "subjectLabel": p.course.subject.label,
            "level": p.course.level,
            "hours": p.course.hours,
            "completedAt": p.updated_at,
        }
        for p in qs
    ]


# ───────────────────────────── Learner: badges ─────────────────────────────

def recent_badges(user, limit: int = MAX_RECENT_BADGES):
    """
    Most recently issued badges for the dashboard wallet strip.

    `pngUrl` is always a string or None. Never returns the FieldFile
    object, which was the source of a UnicodeDecodeError when DRF tried
    to serialize the file's raw bytes.
    """
    qs = badges_for_user(user).order_by("-issued_at")[:limit]
    return [
        {
            "id": str(b.id),
            "badgeId": b.badge_id,
            "earnedAt": b.issued_at,
            "courseTitle": _snapshot_get(b, "course_title", b.course.title),
            "subject": _snapshot_get(b, "subject", b.course.subject.slug),
            "subjectLabel": _snapshot_get(b, "subject_label", b.course.subject.label),
            "pngUrl": _safe_file_url(b.png_file),      # ← never returns bytes
        }
        for b in qs
    ]


# ───────────────────────────── Learner: activity + streak ─────────────────────────────

def weekly_activity(user, days: int = ACTIVITY_WINDOW_DAYS):
    """
    Returns a list of { date, label, value, percent } for the last N
    days, ending today.
    """
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    rows = (
        DailyActivity.objects
        .filter(user=user, date__gte=start, date__lte=today)
        .values("date", "lessons_completed")
    )
    by_date = {r["date"]: r["lessons_completed"] for r in rows}

    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    buckets = []
    peak = 1
    for i in range(days):
        d = start + timedelta(days=i)
        value = by_date.get(d, 0)
        peak = max(peak, value)
        buckets.append({
            "date": d.isoformat(),
            "label": labels[d.weekday()],
            "value": value,
        })

    return [{**b, "percent": round((b["value"] / peak) * 100)} for b in buckets]


def current_streak(user) -> int:
    """
    Number of consecutive days (ending today or yesterday) on which the
    user completed at least one lesson.
    """
    today = timezone.localdate()
    active_days = set(
        DailyActivity.objects
        .filter(user=user, lessons_completed__gte=1)
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


# ───────────────────────────── Learner: aggregated stats ─────────────────────────────

def learner_stats(user):
    completed = CourseProgress.objects.filter(user=user, percent__gte=100).count()
    started = CourseProgress.objects.filter(user=user, percent__gt=0).count()
    badges = Badge.objects.filter(user=user, status=Badge.Status.ISSUED).count()

    minutes = sum(
        LessonCompletion.objects
        .filter(user=user)
        .values_list("lesson__minutes", flat=True)
    )

    return {
        "coursesStarted": started,
        "coursesCompleted": completed,
        "badgesEarned": badges,
        "lessonsCompleted": LessonCompletion.objects.filter(user=user).count(),
        "minutesLearned": minutes,
        "streak": current_streak(user),
    }


# ───────────────────────────── Recommendations ─────────────────────────────

def recommended_courses(user, limit: int = MAX_RECOMMENDED):
    """
    Prefer courses in the user's preferred value chains, then popular
    ones. Exclude any course the user has already started or completed.
    """
    started_course_ids = set(
        CourseProgress.objects.filter(user=user).values_list("course_id", flat=True)
    )

    profile = getattr(user, "profile", None)
    value_chain_ids = []
    if profile:
        value_chain_ids = list(profile.value_chains.values_list("id", flat=True))

    base = Course.objects.published().exclude(id__in=started_course_ids)

    if value_chain_ids:
        preferred = list(
            base.filter(subject_id__in=value_chain_ids)
            .order_by("-popular", "-rating")[:limit]
        )
        if len(preferred) < limit:
            extras = list(
                base.exclude(id__in=[c.id for c in preferred])
                .order_by("-popular", "-rating")[: limit - len(preferred)]
            )
            qs = preferred + extras
        else:
            qs = preferred
    else:
        qs = list(base.order_by("-popular", "-rating")[:limit])

    return [
        {
            "id": str(c.id),
            "slug": c.slug,
            "title": c.title,
            "summary": c.summary,
            "image": c.image_url,                    
            "alt": c.alt_text,
            "subject": c.subject.slug,
            "subjectLabel": c.subject.label,
            "level": c.level,
            "levelLabel": c.get_level_display(),
            "rating": _dec(c.rating),
            "hours": c.hours,
            "lessons": c.lesson_count,
        }
        for c in qs
    ]


# ───────────────────────────── Learner: field days ─────────────────────────────

def nearby_field_days(user, limit: int = MAX_FIELD_DAYS):
    county = getattr(getattr(user, "profile", None), "county", None)
    events = list(upcoming_field_days(county=county, limit=limit))

    if len(events) < limit and county:
        extras = [
            e for e in upcoming_field_days(limit=limit) if e not in events
        ][: limit - len(events)]
        events += extras

    return [
        {
            "id": str(e.id),
            "slug": e.slug,
            "title": e.title,
            "county": e.county.name,
            "venue": e.venue,
            "startsAt": e.starts_at,
            "endsAt": e.ends_at,
            "topic": e.topic.slug,
            "topicLabel": e.topic.label,
            "spots": e.spots,
            "spotsLeft": e.spots_left,
        }
        for e in events
    ]


# ───────────────────────────── County dashboards ─────────────────────────────

def county_enrolment_series(county_id, *, weeks: int = 8):
    """
    Weekly enrolment count for the last N weeks in a given county.

    Uses Django's TruncWeek rather than raw `.extra()` so the query
    works on both PostgreSQL and SQLite (dev).
    """
    from django.db.models.functions import TruncWeek

    today = timezone.localdate()
    start = today - timedelta(weeks=weeks)

    qs = (
        User.objects
        .filter(profile__county_id=county_id, created_at__date__gte=start)
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(n=Count("id"))
        .order_by("week")
    )
    return [
        {"week": r["week"].date().isoformat(), "count": r["n"]}
        for r in qs
        if r["week"] is not None
    ]


def county_completion_rate(county_id):
    """
    Course completions ÷ course starts, by subject.
    """
    rows = (
        CourseProgress.objects
        .filter(user__profile__county_id=county_id)
        .values("course__subject__slug", "course__subject__label")
        .annotate(
            started=Count("id", distinct=True),
            completed=Count("id", filter=Q(percent__gte=100), distinct=True),
        )
    )
    return [
        {
            "subject": r["course__subject__slug"],
            "subjectLabel": r["course__subject__label"],
            "started": r["started"],
            "completed": r["completed"],
            "rate": round((r["completed"] / r["started"]) * 100, 1) if r["started"] else 0,
        }
        for r in rows
    ]


def county_demographics(county_id):
    """
    Gender + youth split for a county, for partner reporting.

    The youth count uses a Python-side filter instead of raw SQL, so
    it works on both PostgreSQL and SQLite.
    """
    rows = (
        User.objects
        .filter(profile__county_id=county_id)
        .values("profile__gender")
        .annotate(n=Count("id"))
    )
    by_gender = {r["profile__gender"] or "unknown": r["n"] for r in rows}

    today = timezone.localdate()
    cutoff_young = today.replace(year=today.year - 18)
    cutoff_old = today.replace(year=today.year - 35)

    youth = (
        User.objects
        .filter(
            profile__county_id=county_id,
            profile__date_of_birth__isnull=False,
            profile__date_of_birth__lte=cutoff_young,
            profile__date_of_birth__gte=cutoff_old,
        )
        .count()
    )

    total = sum(by_gender.values())
    return {
        "total": total,
        "byGender": by_gender,
        "youth": youth,
        "youthShare": round((youth / total) * 100, 1) if total else 0,
    }


def county_field_day_stats(county_id):
    from apps.fielddays.models import Booking, FieldDay

    events = FieldDay.objects.filter(county_id=county_id, status="published")
    total_events = events.count()
    total_bookings = Booking.objects.filter(field_day__county_id=county_id).count()
    attended = Booking.objects.filter(
        field_day__county_id=county_id, status="attended",
    ).count()

    return {
        "events": total_events,
        "bookings": total_bookings,
        "attended": attended,
        "attendanceRate": round((attended / total_bookings) * 100, 1) if total_bookings else 0,
    }