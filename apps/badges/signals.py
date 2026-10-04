# apps/badges/signals.py
"""
Signal handlers that drive automatic badge issuance.

The trigger is `LessonCompletion` — when a learner completes every
lesson in a course, we issue a badge. This keeps the logic in one
place regardless of whether the completion came from the web UI,
mobile app, or an admin action.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.progress.models import LessonCompletion
from apps.courses.models import Lesson

from .services import issue_badge

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LessonCompletion, dispatch_uid="badges.on_lesson_completed")
def on_lesson_completed(sender, instance, created, **kwargs):
    if not created:
        return

    course = instance.course
    user = instance.user

    total = Lesson.objects.filter(module__course=course).count()
    done = LessonCompletion.objects.filter(user=user, course=course).count()

    if total and done >= total:
        try:
            issue_badge(user, course)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to issue badge for user=%s course=%s",
                user.id, course.slug,
            )