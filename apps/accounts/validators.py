# apps/accounts/validators.py
from django.core.exceptions import ValidationError

from .constants import DISALLOWED_EMAIL_DOMAINS


def validate_not_disallowed_email(value: str):
    """Reject throwaway / placeholder email domains."""
    if not value or "@" not in value:
        return
    domain = value.rsplit("@", 1)[-1].lower()
    if domain in DISALLOWED_EMAIL_DOMAINS:
        raise ValidationError(
            f"Email addresses from {domain} are not accepted."
        )


def validate_kenyan_id(value: str):
    """National ID / passport: 7–9 digits (ID) or 8+ alphanumeric (passport)."""
    if not value:
        return
    cleaned = value.strip()
    if cleaned.isdigit() and 7 <= len(cleaned) <= 9:
        return
    if cleaned.isalnum() and 8 <= len(cleaned) <= 12:
        return
    raise ValidationError("Enter a valid Kenyan ID or passport number.")