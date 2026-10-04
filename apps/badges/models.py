# apps/badges/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class BadgeTemplate(TimeStampedModel):
    """
    Visual identity for badges in a given Subject. One row per subject.
    Falls back to platform defaults when a subject has no template.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.OneToOneField(
        "courses.Subject",
        on_delete=models.CASCADE,
        related_name="badge_template",
    )
    tint_hex = models.CharField(max_length=7, default="#23804A")
    accent_hex = models.CharField(max_length=7, default="#F0B429")
    icon = models.CharField(max_length=60, blank=True)
    label = models.CharField(
        max_length=60, blank=True,
        help_text="Optional override for the subject label shown on the badge.",
    )

    class Meta:
        verbose_name = "Badge template"
        verbose_name_plural = "Badge templates"

    def __str__(self):
        return f"Template · {self.subject.label}"

    @property
    def display_label(self):
        return self.label or self.subject.label


class BadgeQuerySet(models.QuerySet):
    def issued(self):
        return self.filter(status=Badge.Status.ISSUED)

    def revoked(self):
        return self.filter(status=Badge.Status.REVOKED)

    def for_user(self, user):
        return self.filter(user=user)

    def active(self):
        """Issued badges that are not expired."""
        now = timezone.now()
        return self.issued().filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )


class Badge(TimeStampedModel):
    """
    A single badge earned by a user for completing a course.

    The `snapshot` field freezes the course metadata at issuance time so
    public verification keeps working even if the course is later
    renamed, retitled, or archived.
    """
    class Status(models.TextChoices):
        ISSUED  = "issued",  "Issued"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    badge_id = models.CharField(
        max_length=32, unique=True, db_index=True,
        help_text="Public verifiable ID, e.g. KALRO-B-2025-001847",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="badges",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="badges",
    )

    issued_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ISSUED, db_index=True,
    )

    # Frozen metadata captured at issuance time
    snapshot = models.JSONField(default=dict, blank=True)

    # Rasterised badge (filled in by a Celery task)
    png_file = models.FileField(upload_to="badges/png/", blank=True)

    objects = BadgeQuerySet.as_manager()

    class Meta:
        ordering = ["-issued_at"]
        unique_together = [("user", "course")]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "issued_at"]),
            models.Index(fields=["course", "status"]),
        ]
        verbose_name = "Badge"
        verbose_name_plural = "Badges"

    def __str__(self):
        return f"{self.badge_id} · {self.user.email} · {self.course.title}"

    # ── Convenience ──────────────────────────────────────────────
    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_verifiable(self) -> bool:
        return self.status == self.Status.ISSUED and not self.is_expired

    def revoke(self, reason: str = ""):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        if reason:
            self.snapshot["revoke_reason"] = reason
        self.save(update_fields=["status", "revoked_at", "snapshot", "updated_at"])


class BadgeVerification(TimeStampedModel):
    """
    Audit trail of public verification lookups. Useful for analytics
    (how often badges are checked by employers, cooperatives, etc.).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    badge = models.ForeignKey(
        Badge, on_delete=models.CASCADE, related_name="verifications"
    )
    verifier_ip = models.GenericIPAddressField(null=True, blank=True)
    verifier_ua = models.CharField(max_length=220, blank=True)
    verifier_referer = models.URLField(max_length=300, blank=True)
    verified_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-verified_at"]
        verbose_name = "Badge verification"
        verbose_name_plural = "Badge verifications"

    def __str__(self):
        return f"{self.badge.badge_id} verified at {self.verified_at:%Y-%m-%d %H:%M}"