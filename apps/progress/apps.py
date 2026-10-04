# apps/progress/apps.py
from django.apps import AppConfig


class ProgressConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.progress"
    label = "progress"
    verbose_name = "Learner Progress"

    def ready(self):
        from . import signals  # noqa: F401