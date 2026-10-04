# apps/media/models.py
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from .constants import (
    STATUS_PENDING,
    STATUS_UPLOADING,
    STATUS_PROCESSING,
    STATUS_READY,
    STATUS_FAILED,
)
from .validators import (
    validate_video_upload,
    validate_pdf_upload,
    validate_image_upload,
)


class MediaQuerySet(models.QuerySet):
    def ready(self):
        return self.filter(status=STATUS_READY)

    def videos(self):
        return self.filter(kind=MediaAsset.Kind.VIDEO)

    def pdfs(self):
        return self.filter(kind=MediaAsset.Kind.PDF)

    def for_uploader(self, user):
        return self.filter(uploaded_by=user)


class MediaAsset(TimeStampedModel):
    """
    A single piece of media — a video manifest, a PDF, or an image
    poster. Attached to a lesson or resource from the courses app.

    Videos here always point to an HLS/DASH manifest URL. We never store
    raw segment files; those live on the CDN or S3 bucket.
    """
    class Kind(models.TextChoices):
        VIDEO  = "video",  "Video (HLS/DASH manifest)"
        PDF    = "pdf",    "PDF document"
        IMAGE  = "image",  "Image"

    class Status(models.TextChoices):
        PENDING    = STATUS_PENDING,    "Pending upload"
        UPLOADING  = STATUS_UPLOADING,  "Uploading"
        PROCESSING = STATUS_PROCESSING, "Processing"
        READY      = STATUS_READY,      "Ready"
        FAILED     = STATUS_FAILED,     "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    kind = models.CharField(max_length=8, choices=Kind.choices, db_index=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True,
    )

    title = models.CharField(max_length=180, blank=True)

    # Actual stored file (used for PDFs and images; for videos it's the
    # optional poster frame or the raw upload kept as a fallback source).
    file = models.FileField(
        upload_to="media/", blank=True,
        help_text="Stored file path or S3 key.",
    )

    # For videos: the public CDN base + path to the manifest.
    # Example: https://cdn.kalro.org/hls/dairy-m2l1/master.m3u8
    manifest_url = models.URLField(blank=True)
    # Optional: separate path to the folder containing the segments.
    segments_base_url = models.URLField(blank=True)

    # For images: thumbnail / poster frame
    poster_url = models.URLField(blank=True)

    # Metadata
    mime_type = models.CharField(max_length=80, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # Ownership
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_media",
    )

    # Extras
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)

    objects = MediaQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "status"]),
            models.Index(fields=["uploaded_by", "kind"]),
        ]
        verbose_name = "Media asset"
        verbose_name_plural = "Media assets"

    def __str__(self):
        return f"{self.get_kind_display()} · {self.slug}"

    @property
    def is_ready(self) -> bool:
        return self.status == STATUS_READY

    def mark_ready(self):
        self.status = STATUS_READY
        self.error_message = ""
        self.save(update_fields=["status", "error_message", "updated_at"])

    def mark_failed(self, message: str):
        self.status = STATUS_FAILED
        self.error_message = message
        self.save(update_fields=["status", "error_message", "updated_at"])


class UploadSession(TimeStampedModel):
    """
    Tracks a resumable / chunked upload initiated by the client.

    For small PDFs and posters, the React app can upload directly to
    Django with a multipart POST. For large videos, the client requests
    a session here, gets a pre-signed S3 POST, uploads chunks, then
    calls `/complete/` — and we mark the MediaAsset ready.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        MediaAsset, on_delete=models.CASCADE, related_name="upload_sessions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="upload_sessions",
    )
    expected_size = models.BigIntegerField(null=True, blank=True)
    received_bytes = models.BigIntegerField(default=0)
    upload_url = models.URLField(blank=True)
    upload_fields = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Upload session"
        verbose_name_plural = "Upload sessions"

    def __str__(self):
        return f"Session for {self.asset.slug}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def percent(self) -> int:
        if not self.expected_size:
            return 0
        return min(100, round((self.received_bytes / self.expected_size) * 100))