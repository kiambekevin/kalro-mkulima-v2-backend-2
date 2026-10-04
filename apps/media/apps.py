# apps/media/apps.py
from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.media"
    label = "media_library"        # "media" clashes with Django's settings.MEDIA_*
    verbose_name = "Media Library"

    def ready(self):
        from . import signals  # noqa: F401