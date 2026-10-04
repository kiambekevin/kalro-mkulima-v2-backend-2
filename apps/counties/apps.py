# apps/counties/apps.py
from django.apps import AppConfig


class CountiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.counties"
    label = "counties"
    verbose_name = "Counties & Administrative Units"