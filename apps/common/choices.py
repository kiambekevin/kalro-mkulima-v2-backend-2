# apps/common/choices.py
from django.db import models

from .constants import LANGUAGE_CHOICES


class Language(models.TextChoices):
    EN = "en", "English"
    SW = "sw", "Kiswahili"


class SortOrder(models.TextChoices):
    ASC = "asc", "Ascending"
    DESC = "desc", "Descending"


class Visibility(models.TextChoices):
    PUBLIC = "public", "Public"
    AUTHENTICATED = "authenticated", "Authenticated only"
    STAFF = "staff", "Staff only"