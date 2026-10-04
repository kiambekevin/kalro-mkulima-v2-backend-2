# apps/badges/services.py
"""
Business logic for issuing, revoking and verifying badges.

Kept separate from views and models so the same functions can be called
from signals (on course completion), management commands (bulk re-issue),
or the API layer.
"""
import hashlib
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.models import TimeStampedModel  # noqa: F401 — imported for type hints
from .constants import SNAPSHOT_VERSION
from .models import Badge, BadgeTemplate, BadgeVerification

logger = logging.getLogger(__name__)


# ───────────────────────────── ID generation ─────────────────────────────

def generate_badge_id(course_id, user_id, issued_at) -> str:
    """
    Produces a deterministic-but-unique public ID:
        <PREFIX>-<YEAR>-<6-DIGITS>
    Uses a hash of (course, user, timestamp) so collisions are rare.
    """
    prefix = getattr(settings, "KALRO_BADGE_ID_PREFIX", "KALRO-B")
    year = issued_at.year
    seed = f"{course_id}:{user_id}:{issued_at.isoformat()}"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    number = int(digest[:12], 16) % 1_000_000

    candidate = f"{prefix}-{year}-{number:06d}"
    # Retry on the (very) unlikely collision
    while Badge.objects.filter(badge_id=candidate).exists():
        number = (number + 1) % 1_000_000
        candidate = f"{prefix}-{year}-{number:06d}"
    return candidate


# ───────────────────────────── Issuance ─────────────────────────────

@transaction.atomic
def issue_badge(user, course, *, force: bool = False) -> Badge:
    """
    Issue a badge to `user` for `course`. Idempotent — returns the
    existing badge if one already exists, unless `force=True`.

    Called from:
      - apps/progress.signals when the last lesson is completed
      - Admin bulk actions
      - Demo seeding scripts
    """
    if not course.badge_enabled:
        logger.info("Course %s has badges disabled — skipping.", course.slug)
        return None

    existing = Badge.objects.filter(user=user, course=course).first()
    if existing and not force:
        return existing

    now = timezone.now()
    expires_at = None
    expiry_days = getattr(settings, "KALRO_BADGE_EXPIRY_DAYS", 0)
    if expiry_days:
        from datetime import timedelta
        expires_at = now + timedelta(days=expiry_days)

    snapshot = build_snapshot(course, user, now)

    if existing and force:
        # Re-issue in place
        existing.snapshot = snapshot
        existing.issued_at = now
        existing.expires_at = expires_at
        existing.status = Badge.Status.ISSUED
        existing.revoked_at = None
        existing.save()
        badge = existing
    else:
        badge = Badge.objects.create(
            badge_id=generate_badge_id(course.id, user.id, now),
            user=user,
            course=course,
            issued_at=now,
            expires_at=expires_at,
            snapshot=snapshot,
        )

    # Render PNG + send notification asynchronously
    from .tasks import render_badge_png_task, send_badge_email_task
    render_badge_png_task.delay(badge.id)
    send_badge_email_task.delay(badge.id)

    logger.info("Issued badge %s to %s for %s", badge.badge_id, user.email, course.slug)
    return badge


def build_snapshot(course, user, issued_at) -> dict:
    """
    Freeze the metadata needed to verify or display the badge even if
    the course is later edited or archived.
    """
    return {
        "version": SNAPSHOT_VERSION,
        "course_id": str(course.id),
        "course_slug": course.slug,
        "course_title": course.title,
        "subject": course.subject.slug,
        "subject_label": course.subject.label,
        "level": course.level,
        "hours": course.hours,
        "instructor": getattr(course.instructor, "full_name", None)
            if course.instructor else None,
        "issued_at": issued_at.isoformat(),
        "recipient": {
            "full_name": user.full_name,
            "first_name": user.first_name,
            "initials": user.initials,
            "county": getattr(getattr(user.profile, "county", None), "name", None),
        },
    }


@transaction.atomic
def revoke_badge(badge: Badge, *, reason: str = "") -> Badge:
    badge.revoke(reason=reason)
    return badge


@transaction.atomic
def reverify_badge(badge: Badge) -> Badge:
    """Reset a revoked badge back to issued state (rare — admin only)."""
    badge.status = Badge.Status.ISSUED
    badge.revoked_at = None
    badge.save(update_fields=["status", "revoked_at", "updated_at"])
    return badge


# ───────────────────────────── Verification ─────────────────────────────

def verify_badge(badge_id: str, *, request=None) -> tuple[Badge | None, str]:
    """
    Look up a badge and record the verification hit.

    Returns (badge_or_none, reason):
      - ("ok")               — badge exists and is verifiable
      - ("not_found")        — no badge with this ID
      - ("revoked")          — badge was revoked
      - ("expired")          — badge has passed its expiry
    """
    badge = (
        Badge.objects
        .select_related("user", "user__profile", "user__profile__county", "course", "course__subject")
        .filter(badge_id__iexact=badge_id)
        .first()
    )
    if badge is None:
        return None, "not_found"

    reason = "ok"
    if badge.status == Badge.Status.REVOKED:
        reason = "revoked"
    elif badge.is_expired:
        reason = "expired"

    log_verification(badge, request=request, reason=reason)
    return badge, reason


def log_verification(badge: Badge, *, request=None, reason: str = "ok"):
    """Record the verification for analytics."""
    ip = ua = ref = None
    if request is not None:
        ip = _client_ip(request)
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:220]
        ref = (request.META.get("HTTP_REFERER") or "")[:300]

    BadgeVerification.objects.create(
        badge=badge,
        verifier_ip=ip,
        verifier_user_agent=ua,
        verifier_referer=ref,
    )


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ───────────────────────────── Templates ─────────────────────────────

@transaction.atomic
def ensure_template_for_subject(subject) -> BadgeTemplate:
    """Get-or-create a BadgeTemplate for a subject using safe defaults."""
    template, _ = BadgeTemplate.objects.get_or_create(
        subject=subject,
        defaults={
            "tint_hex": "#23804A",
            "accent_hex": "#F0B429",
            "icon": "fa-solid fa-award",
        },
    )
    return template