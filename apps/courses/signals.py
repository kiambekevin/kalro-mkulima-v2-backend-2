# apps/courses/signals.py
"""
Auto-refresh course stats when modules or lessons change, and clear
cached catalogue entries.
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .constants import CATALOGUE_CACHE_TTL, COURSE_DETAIL_CACHE_TTL
from .models import Course, Module, Lesson, Resource


def _clear_course_cache(course_slug):
    cache.delete(f"course:detail:{course_slug}")
    cache.delete("course:catalogue")


@receiver(post_save, sender=Course)
@receiver(post_delete, sender=Course)
def on_course_change(sender, instance, **kwargs):
    _clear_course_cache(getattr(instance, "slug", None))


@receiver(post_save, sender=Module)
@receiver(post_delete, sender=Module)
def on_module_change(sender, instance, **kwargs):
    course = getattr(instance, "course", None)
    if course:
        _clear_course_cache(course.slug)
        from .services import refresh_course_stats
        refresh_course_stats(course)


@receiver(post_save, sender=Lesson)
@receiver(post_delete, sender=Lesson)
def on_lesson_change(sender, instance, **kwargs):
    course = getattr(instance.module, "course", None) if instance.module_id else None
    if course:
        _clear_course_cache(course.slug)
        from .services import refresh_course_stats
        refresh_course_stats(course)


@receiver(post_save, sender=Resource)
@receiver(post_delete, sender=Resource)
def on_resource_change(sender, instance, **kwargs):
    lesson = getattr(instance, "lesson", None)
    if lesson and lesson.module_id:
        course = lesson.module.course
        _clear_course_cache(course.slug)