# apps/dashboard/services.py
"""
Assembles the JSON payloads returned by the dashboard endpoints.

The views are thin — they delegate to `build_learner_dashboard` and
`build_county_dashboard`, which combine the raw queries from
`selectors.py` with caching.
"""
import logging

from django.db.models.fields.files import FieldFile
from django.utils import timezone

from . import cache as dash_cache
from .selectors import (
    completed_courses,
    county_completion_rate,
    county_demographics,
    county_enrolment_series,
    county_field_day_stats,
    in_progress_courses,
    learner_stats,
    nearby_field_days,
    recent_badges,
    recommended_courses,
    weekly_activity,
)

logger = logging.getLogger(__name__)


def _sanitize_value(val):
    """
    Recursively cleans payloads to prevent raw PNG bytes (`bytes`/`memoryview`)
    or unsaved FieldFiles from causing UnicodeDecodeError during JSON serialization.
    """
    if isinstance(val, (bytes, memoryview)):
        # Binary data (e.g. b'\x89PNG...') cannot be decoded as UTF-8
        return None
    if isinstance(val, FieldFile):
        try:
            return val.url if val else None
        except ValueError:
            return None
    if hasattr(val, "url"):
        try:
            return val.url
        except (ValueError, AttributeError):
            return None
    if isinstance(val, dict):
        return {
            k: _sanitize_value(v)
            for k, v in val.items()
            if k not in ("png_bytes", "raw_png")
        }
    if isinstance(val, list):
        return [_sanitize_value(item) for item in val]
    return val


def _format_badges(badges):
    """
    Ensures badge objects/dictionaries use valid URL strings instead of raw binary files.
    """
    if not badges:
        return []

    sanitized = _sanitize_value(badges)
    result = []
    for item in sanitized:
        if isinstance(item, dict):
            if "png_file" in item and "png_url" not in item:
                item["png_url"] = item.pop("png_file")
            result.append(item)
        else:
            result.append(item)
    return result


# ───────────────────────────── Learner ─────────────────────────────

def build_learner_dashboard(user, *, use_cache: bool = True) -> dict:
    """
    Everything the React dashboard page needs in one payload.
    """
    if use_cache:
        cached = dash_cache.get_learner_dashboard(user.id)
        if cached:
            return cached

    data = {
        "user": {
            "id": str(user.id),
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            "role": user.role,
            "county": getattr(getattr(user.profile, "county", None), "name", None),
            "preferredLanguage": user.preferred_language,
        },
        "stats": _sanitize_value(learner_stats(user)),
        "inProgress": _sanitize_value(in_progress_courses(user)),
        "completed": _sanitize_value(completed_courses(user)),
        "recentBadges": _format_badges(recent_badges(user)),
        "weeklyActivity": _sanitize_value(weekly_activity(user)),
        "recommended": _sanitize_value(recommended_courses(user)),
        "fieldDays": _sanitize_value(nearby_field_days(user)),
        "generatedAt": timezone.now().isoformat(),
    }

    if use_cache:
        dash_cache.set_learner_dashboard(user.id, data)

    return data


# ───────────────────────────── County ─────────────────────────────

def build_county_dashboard(county, *, use_cache: bool = True) -> dict:
    """
    Aggregated statistics for a county — for county officers and
    development partners.
    """
    if use_cache:
        cached = dash_cache.get_county_dashboard(county.id)
        if cached:
            return cached

    data = {
        "county": {
            "id": str(county.id),
            "code": county.code,
            "name": county.name,
            "region": county.region,
        },
        "demographics": _sanitize_value(county_demographics(county.id)),
        "enrolmentSeries": _sanitize_value(county_enrolment_series(county.id)),
        "completionBySubject": _sanitize_value(county_completion_rate(county.id)),
        "fieldDayStats": _sanitize_value(county_field_day_stats(county.id)),
        "generatedAt": timezone.now().isoformat(),
    }

    if use_cache:
        dash_cache.set_county_dashboard(county.id, data)

    return data