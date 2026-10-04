# apps/progress/tasks.py
"""
Periodic jobs to keep rollups and daily activity accurate at scale.
"""
import logging

from celery import shared_task
from django.utils import timezone

from .models import CourseProgress, DailyActivity, LessonCompletion

logger = logging.getLogger(__name__)


@shared_task
def recompute_daily_activity_for_user(user_id, target_date=None):
    """Refresh a single user's DailyActivity row."""
    from apps.accounts.models import User
    from .selectors import recompute_daily_activity

    user = User.objects.filter(id=user_id).first()
    if not user:
        return

    target = None
    if target_date:
        from datetime import date
        try:
            target = date.fromisoformat(target_date)
        except ValueError:
            target = None

    recompute_daily_activity(user, target_date=target)


@shared_task
def rebuild_stale_course_progress():
    """
    Runs nightly — rebuilds CourseProgress for any course whose
    `total_count` no longer matches the actual lesson count (a sign
    the curriculum changed since last recalc).
    """
    from apps.courses.models import Lesson
    from django.db.models import Count, F

    rows = (
        CourseProgress.objects
        .annotate(actual_total=Count("course__modules__lessons"))
        .filter(actual_total__gt=0)
        .exclude(actual_total=F("total_count"))
    )

    count = 0
    for cp in rows.iterator():
        cp.recalculate()
        count += 1

    logger.info("Rebuilt %d stale CourseProgress rows.", count)
    return count


@shared_task
def backfill_recent_daily_activity(days: int = 7):
    """
    Runs hourly — ensures the last N days of DailyActivity are
    up-to-date for users who completed lessons via the admin.
    """
    from datetime import date, timedelta
    from apps.accounts.models import User
    from .selectors import recompute_daily_activity

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    user_ids = set(
        LessonCompletion.objects
        .filter(completed_at__date__gte=start)
        .values_list("user_id", flat=True)
        .distinct()
    )

    count = 0
    for uid in user_ids:
        user = User.objects.filter(id=uid).first()
        if not user:
            continue
        for i in range(days):
            target = start + timedelta(days=i)
            recompute_daily_activity(user, target_date=target)
        count += 1

    logger.info("Backfilled daily activity for %d user(s).", count)
    return count