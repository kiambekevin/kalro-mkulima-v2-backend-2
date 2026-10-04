# apps/common/fields.py
"""
Custom model fields used across the project.
"""
from django.core.validators import RegexValidator
from django.db import models


class LowerEmailField(models.EmailField):
    """
    EmailField that lowercases its value on save. Useful for case-
    insensitive uniqueness without a functional index.
    """

    def to_python(self, value):
        value = super().to_python(value)
        return value.lower() if value else value

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        value = value.lower() if value else value
        setattr(model_instance, self.attname, value)
        return value


class HexColourField(models.CharField):
    """
    A 7-character hex colour like `#123B26`, with basic validation.
    """
    default_validators = [
        RegexValidator(
            regex=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
            message="Enter a hex colour like #123B26 or #ABC.",
        ),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 7)
        super().__init__(*args, **kwargs)


class KenyanPhoneField(models.CharField):
    """
    Stores Kenyan phone numbers in E.164 form (e.g. +254712345678).
    Consider using `phonenumber_field` instead if you need full intl
    formatting; this is a lightweight alternative for Kenya-only apps.
    """
    default_validators = [
        RegexValidator(
            regex=r"^(?:\+?254|0)(?:7\d{8}|1\d{8})$",
            message="Enter a valid Kenyan phone number.",
        ),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 20)
        super().__init__(*args, **kwargs)