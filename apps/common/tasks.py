# apps/common/tasks.py
"""
Shared maintenance jobs.
"""
import logging

from celery import shared_task

from .constants import SOFT_DELETE_RETENTION_DAYS

logger = logging.getLogger(__name__)


@shared_task
def purge_old_soft_deleted_rows():
    """
    Hard-deletes rows that were soft-deleted more than
    SOFT_DELETE_RETENTION_DAYS ago.

    Add models to the `targets` list as they adopt SoftDeleteModel.
    """
    from datetime import timedelta
    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=SOFT_DELETE_RETENTION_DAYS)
    targets = []  # e.g. [("courses", "Course"), ("badges", "Badge")]

    total = 0
    for app_label, model_name in targets:
        from django.apps import apps
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        qs = Model.objects_all.filter(deleted_at__lt=cutoff)
        count = qs.delete()[0]
        total += count
        logger.info("Purged %d old %s rows.", count, model_name)

    return total