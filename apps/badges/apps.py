# apps/badges/apps.py
from django.apps import AppConfig


class BadgesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.badges"
    label = "badges"
    verbose_name = "Digital Badges"

    def ready(self):
        from . import signals  # noqa: F401