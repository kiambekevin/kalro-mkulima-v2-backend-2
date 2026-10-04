# apps/progress/signals.py
"""
Keeps CourseProgress, DailyActivity and Badge issuance coherent when
LessonCompletion rows change.
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import CourseProgress, DailyActivity, LessonCompletion

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LessonCompletion)
def on_completion_created(sender, instance, created, **kwargs):
    """
    The service layer already updates rollups during normal flows, but
    admin-created rows (via Django admin) bypass the service and land
    here. Keep rollups coherent in that case.
    """
    if not created:
        return

    cp, _ = CourseProgress.objects.get_or_create(
        user=instance.user, course=instance.course,
    )
    cp.recalculate()

    # Refresh today's daily activity
    try:
        from .selectors import recompute_daily_activity
        recompute_daily_activity(instance.user, target_date=instance.completed_at.date())
    except Exception:  # noqa: BLE001
        logger.exception("Failed to update DailyActivity after completion.")

    # Fire badge issuance if the course just became complete
    if cp.percent >= 100:
        try:
            from apps.badges.services import issue_badge
            issue_badge(instance.user, instance.course)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to issue badge after course completion.")


@receiver(post_delete, sender=LessonCompletion)
def on_completion_deleted(sender, instance, **kwargs):
    """
    Recalculate the rollup when a completion is removed (usually via
    the service, but this covers admin deletes too).
    """
    cp = CourseProgress.objects.filter(
        user=instance.user, course=instance.course,
    ).first()
    if cp:
        cp.recalculate()

    try:
        from .selectors import recompute_daily_activity
        recompute_daily_activity(instance.user, target_date=instance.completed_at.date())
    except Exception:  # noqa: BLE001
        logger.exception("Failed to update DailyActivity after uncompletion.")