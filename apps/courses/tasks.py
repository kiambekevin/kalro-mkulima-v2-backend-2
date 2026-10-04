# apps/courses/tasks.py
import logging

from celery import shared_task

from .models import Course
from .services import publish_course, PublishError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def publish_course_task(self, course_id):
    """Publish a course from a queued admin action."""
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return
    try:
        publish_course(course)
    except PublishError as exc:
        logger.warning("Publish failed for %s: %s", course.slug, exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task
def warm_catalogue_cache():
    """Precompute the catalogue list for the homepage Popular strip."""
    from django.core.cache import cache
    from .selectors import popular_courses
    from .serializers import CourseListSerializer
    from .constants import CATALOGUE_CACHE_TTL

    data = CourseListSerializer(popular_courses(6), many=True).data
    cache.set("course:popular", data, CATALOGUE_CACHE_TTL)
    return len(data)