# apps/common/validators.py
"""
Reusable validators. Keep them small and side-effect free so they can be
called from serializers, models, and forms alike.
"""
import re

from django.core.exceptions import ValidationError

from .constants import KENYA_REGIONS


# ────────────────────────────── Regexes ──────────────────────────────

KENYAN_PHONE_RE = re.compile(r"^(?:\+?254|0)(?:7\d{8}|1\d{8})$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX_COLOUR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# ────────────────────────────── Functions ──────────────────────────────

def validate_kenyan_phone(value: str):
    if not value:
        return
    if not KENYAN_PHONE_RE.match(value.strip()):
        raise ValidationError("Enter a valid Kenyan phone number.")


def validate_slug(value: str):
    if not value:
        return
    if not SLUG_RE.match(value):
        raise ValidationError("Slugs may only contain lowercase letters, numbers and hyphens.")


def validate_hex_colour(value: str):
    if not value:
        return
    if not HEX_COLOUR_RE.match(value):
        raise ValidationError("Enter a hex colour like #123B26 or #ABC.")


def validate_kenya_region(value: str):
    if not value:
        return
    if value not in KENYA_REGIONS:
        raise ValidationError(f"Unknown region: {value}.")


def validate_no_profanity(value: str):
    """
    Placeholder for content moderation. Swap in a real list or an API
    call for production use.
    """
    blocked = {"spamword"}  # extend as needed
    if any(word in value.lower() for word in blocked):
        raise ValidationError("This text contains disallowed words.")


def validate_file_size(max_mb: int):
    """
    Returns a validator callable for FileField(validators=[...]).
    """
    limit = max_mb * 1024 * 1024

    def _validate(file):
        if file.size > limit:
            raise ValidationError(f"File exceeds {max_mb} MB.")

    return _validate