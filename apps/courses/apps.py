# apps/courses/apps.py
from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.courses"
    label = "courses"
    verbose_name = "Courses & Curriculum"

    def ready(self):
        from . import signals  # noqa: F401