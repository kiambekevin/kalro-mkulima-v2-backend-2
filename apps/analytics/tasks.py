# apps/analytics/tasks.py
import logging
from datetime import date, timedelta

from celery import shared_task
from django.db.models import Count
from django.db.models.functions import TruncDate

from .models import DailyVisitRollup, VisitEvent

logger = logging.getLogger(__name__)


@shared_task
def build_daily_rollup(for_date: str | None = None):
    """
    Aggregate yesterday's visit events into DailyVisitRollup.
    Idempotent — safe to re-run.
    """
    if for_date:
        target = date.fromisoformat(for_date)
    else:
        target = date.today() - timedelta(days=1)

    # Clear existing rollups for the day (idempotent re-run)
    DailyVisitRollup.objects.filter(date=target).delete()

    rows = (
        VisitEvent.objects
        .filter(created_at__date=target)
        .values("resource_type", "course_id", "lesson_id", "county_id")
        .annotate(count=Count("id"))
    )

    bulk = [
        DailyVisitRollup(
            date=target,
            resource_type=r["resource_type"],
            course_id=r["course_id"],
            lesson_id=r["lesson_id"],
            county_id=r["county_id"],
            count=r["count"],
        )
        for r in rows
    ]
    DailyVisitRollup.objects.bulk_create(bulk, batch_size=500)
    logger.info("Rolled up %d rows for %s", len(bulk), target)
    return len(bulk)


@shared_task
def prune_old_visit_events(days: int = 365):
    """Delete raw events older than `days` — the rollups keep the history."""
    cutoff = date.today() - timedelta(days=days)
    deleted, _ = VisitEvent.objects.filter(created_at__date__lt=cutoff).delete()
    logger.info("Pruned %d old visit events.", deleted)
    return deleted