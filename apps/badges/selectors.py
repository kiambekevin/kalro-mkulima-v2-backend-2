# apps/badges/selectors.py
"""
Read-only queries used by views, serializers and reports. Keeps views
free of ORM detail and makes query optimisation explicit.
"""
from django.db.models import Prefetch

from .models import Badge, BadgeVerification


def badges_for_user(user):
    """All badges for a user, with everything the wallet page needs."""
    return (
        Badge.objects
        .filter(user=user)
        .select_related("course", "course__subject")
        .order_by("-issued_at")
    )


def active_badges_for_user(user):
    return badges_for_user(user).active()


def badge_by_public_id(badge_id: str):
    """Single badge lookup for verification endpoints (case-insensitive)."""
    return (
        Badge.objects
        .select_related(
            "user", "user__profile", "user__profile__county",
            "course", "course__subject",
        )
        .filter(badge_id__iexact=badge_id)
        .first()
    )


def recent_badges(limit: int = 10):
    """For county / partner dashboards."""
    return (
        Badge.objects
        .issued()
        .select_related("course", "course__subject", "user")
        .order_by("-issued_at")[:limit]
    )


def verifications_for_badge(badge):
    return badge.verifications.all().order_by("-verified_at")