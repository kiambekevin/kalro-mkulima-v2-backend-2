# apps/fielddays/apps.py
from django.apps import AppConfig


class FieldDaysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fielddays"
    label = "fielddays"
    verbose_name = "Field Days & Events"

    def ready(self):
        from . import signals  # noqa: F401