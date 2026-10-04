# apps/common/texts.py
"""
Text helpers specific to KALRO Mkulima. Kept separate from utils.py so
product copy transformations live in one obvious place.
"""
from .utils import initials as _initials, truncate as _truncate


def display_name(user) -> str:
    """Best-effort display name for a user object."""
    if user is None:
        return "Learner"
    first = getattr(user, "first_name", "") or ""
    if first:
        return first
    email = getattr(user, "email", "") or ""
    return email.split("@")[0].title() or "Learner"


def user_initials(user) -> str:
    return _initials(
        getattr(user, "first_name", "") or "",
        getattr(user, "last_name", "") or "",
    )


def greeting_for_now(dt=None) -> str:
    """Returns 'Good morning' / 'Good afternoon' / 'Good evening'."""
    from django.utils import timezone
    dt = dt or timezone.localtime()
    hour = dt.hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def course_title_short(title: str) -> str:
    """Trim a course title to 42 chars for card headers."""
    return _truncate(title, 42)


def subject_chip_label(label: str) -> str:
    """Uppercase and trim a subject label for chips."""
    return _truncate(label.strip().upper(), 20, ellipsis="")