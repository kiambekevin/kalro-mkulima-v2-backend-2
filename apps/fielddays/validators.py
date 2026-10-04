# apps/fielddays/validators.py
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_future_start(value):
    """Field days must be scheduled in the future."""
    if value and value <= timezone.now():
        raise ValidationError("Start time must be in the future.")


def validate_end_after_start(start, end):
    if start and end and end <= start:
        raise ValidationError("End time must be after start time.")


def validate_spots(value):
    if value < 1 or value > 5000:
        raise ValidationError("Spots must be between 1 and 5000.")