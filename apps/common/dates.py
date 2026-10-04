# apps/common/dates.py
"""
Date and time helpers. All functions assume timezone-aware datetimes
unless the parameter explicitly says otherwise.
"""
from datetime import date, datetime, timedelta

from django.utils import timezone


# ────────────────────────────── Ranges ──────────────────────────────

def day_bounds(when: date | None = None) -> tuple[datetime, datetime]:
    """Start/end datetimes for a calendar day in the current TZ."""
    when = when or timezone.localdate()
    start = datetime.combine(when, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


def week_bounds(when: date | None = None) -> tuple[datetime, datetime]:
    """Monday 00:00 → Sunday 23:59:59.999999."""
    when = when or timezone.localdate()
    monday = when - timedelta(days=when.weekday())
    return day_bounds(monday)[0], day_bounds(monday + timedelta(days=6))[1]


def month_bounds(when: date | None = None) -> tuple[datetime, datetime]:
    when = when or timezone.localdate()
    first = when.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    last = next_month - timedelta(days=1)
    return day_bounds(first)[0], day_bounds(last)[1]


# ────────────────────────────── Buckets ──────────────────────────────

def last_n_days(n: int = 7, *, end: date | None = None) -> list[date]:
    """Returns the last N calendar days ending at `end` (default today)."""
    end = end or timezone.localdate()
    return [end - timedelta(days=i) for i in range(n - 1, -1, -1)]


def week_labels(locale: str = "en") -> list[str]:
    """['Mon', 'Tue', …, 'Sun'] for chart axis labels."""
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ────────────────────────────── Formatting ──────────────────────────────

def humanise_duration(seconds: int) -> str:
    """125 → '2 min 5 sec'; 7200 → '2 hrs'."""
    if seconds < 60:
        return f"{seconds} sec"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min" + (f" {sec} sec" if sec else "")
    hours, minutes = divmod(minutes, 60)
    return f"{hours} hr" + (f" {minutes} min" if minutes else "")


def humanise_ago(dt: datetime) -> str:
    """'3 min ago', '2 days ago', 'just now'."""
    if not dt:
        return ""
    delta = timezone.now() - dt
    sec = int(delta.total_seconds())
    if sec < 45:
        return "just now"
    if sec < 60:
        return f"{sec} sec ago"
    mins = sec // 60
    if mins < 60:
        return f"{mins} min ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours} hr ago"
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = months // 12
    return f"{years} year{'s' if years != 1 else ''} ago"


def iso_date(dt: datetime | date | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d")


def iso_datetime(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.isoformat()