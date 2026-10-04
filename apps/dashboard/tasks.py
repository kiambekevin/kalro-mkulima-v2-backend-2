# apps/dashboard/tasks.py
"""
Background jobs that keep dashboard caches fresh.
"""
import logging

from celery import shared_task

from . import cache as dash_cache

logger = logging.getLogger(__name__)


@shared_task
def invalidate_learner_dashboard(user_id):
    """Called by signals when progress or badges change for a user."""
    dash_cache.invalidate_learner(user_id)
    logger.info("Invalidated learner dashboard for %s", user_id)


@shared_task
def invalidate_county_dashboard(county_id):
    dash_cache.invalidate_county(county_id)
    logger.info("Invalidated county dashboard for %s", county_id)


@shared_task
def invalidate_all_dashboards():
    count = dash_cache.invalidate_all()
    logger.info("Invalidated %d dashboard cache entries.", count)
    return count