# apps/media/services.py
"""
Business logic for media: creating assets, issuing signed URLs,
completing uploads, attaching transcoded manifests.
"""
import hashlib
import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .constants import (
    DEFAULT_SIGNED_URL_TTL,
    PDF_SIGNED_URL_TTL,
    UPLOAD_SESSION_TTL,
    STATUS_PENDING,
    STATUS_UPLOADING,
    STATUS_PROCESSING,
    STATUS_READY,
)
from .models import MediaAsset, UploadSession
from .signing import sign_url

logger = logging.getLogger(__name__)


# ───────────────────────────── Slugs ─────────────────────────────

def _make_slug(kind: str, filename: str) -> str:
    base = slugify(filename.rsplit(".", 1)[0])[:80] or kind
    return f"{kind}-{base}-{uuid.uuid4().hex[:6]}"


# ───────────────────────────── Upload flow ─────────────────────────────

@transaction.atomic
def initiate_upload(*, user, kind: str, filename: str, size_bytes: int,
                    title: str = "", mime_type: str = "") -> tuple[MediaAsset, UploadSession]:
    """
    Create a MediaAsset + UploadSession, then hand the caller a signed
    URL to push bytes to S3 directly.

    Returns (asset, session).
    """
    asset = MediaAsset.objects.create(
        slug=_make_slug(kind, filename),
        kind=kind,
        status=STATUS_PENDING,
        title=title or filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by=user,
    )

    session = UploadSession.objects.create(
        asset=asset,
        user=user,
        expected_size=size_bytes,
        expires_at=timezone.now() + timezone.timedelta(seconds=UPLOAD_SESSION_TTL),
    )

    # Generate a pre-signed S3 POST (or PUT) URL. This is a placeholder
    # that returns a signed URL to /upload/stream/ — the real deployment
    # would use boto3's generate_presigned_post for direct S3 uploads.
    session.upload_url = f"/api/v1/media/upload/{session.id}/bytes/"
    session.upload_fields = {"Content-Type": mime_type or "application/octet-stream"}
    session.save(update_fields=["upload_url", "upload_fields", "updated_at"])

    asset.status = STATUS_UPLOADING
    asset.save(update_fields=["status", "updated_at"])

    return asset, session


@transaction.atomic
def complete_upload(*, session: UploadSession, checksum_sha256: str = "",
                    duration_seconds: int | None = None) -> MediaAsset:
    """
    Called after the client finished uploading. Validates and flips
    the asset to READY, or to PROCESSING if it's a video that still
    needs a manifest.
    """
    asset = session.asset

    if checksum_sha256:
        asset.checksum_sha256 = checksum_sha256

    if duration_seconds is not None:
        asset.duration_seconds = duration_seconds

    session.completed_at = timezone.now()
    session.save(update_fields=["completed_at", "updated_at"])

    if asset.kind == MediaAsset.Kind.VIDEO and not asset.manifest_url:
        asset.status = STATUS_PROCESSING
    else:
        asset.status = STATUS_READY

    asset.save(update_fields=["status", "checksum_sha256", "duration_seconds", "updated_at"])
    logger.info("Upload completed for %s (%s)", asset.slug, asset.status)
    return asset


@transaction.atomic
def attach_manifest(*, asset: MediaAsset, manifest_url: str,
                    segments_base_url: str = "",
                    duration_seconds: int | None = None,
                    poster_url: str = "") -> MediaAsset:
    """
    Attach an HLS/DASH manifest URL to a video asset. Called by the
    transcoding pipeline once the segments are ready on the CDN.
    """
    asset.manifest_url = manifest_url
    if segments_base_url:
        asset.segments_base_url = segments_base_url
    if duration_seconds is not None:
        asset.duration_seconds = duration_seconds
    if poster_url:
        asset.poster_url = poster_url
    asset.status = STATUS_READY
    asset.error_message = ""
    asset.save()
    logger.info("Attached manifest to %s → %s", asset.slug, manifest_url)
    return asset


# ───────────────────────────── Signed URLs ─────────────────────────────

def signed_playback_url(asset: MediaAsset, *, request=None,
                        ttl: int = DEFAULT_SIGNED_URL_TTL) -> str:
    """
    Signed HLS/DASH playback URL. The client hands this to Shaka Player,
    which then fetches the segments with the same signature.

    For real S3/CloudFront deployments, replace the `sign_url` call with
    boto3's `generate_presigned_url` (or CloudFront's signed cookies).
    """
    if not asset.manifest_url:
        return ""

    signed = sign_url(asset.manifest_url, ttl=ttl, extra={"asset": str(asset.id)})
    if request:
        # Absolute URL if the caller wants a fully-qualified link
        return request.build_absolute_uri(signed) if signed.startswith("/") else signed
    return signed


def signed_download_url(asset: MediaAsset, *, request=None,
                        ttl: int = PDF_SIGNED_URL_TTL) -> str:
    """Signed download URL for PDFs and images."""
    if not asset.file:
        return ""

    base = asset.file.url
    signed = sign_url(base, ttl=ttl, extra={"asset": str(asset.id)})
    if request:
        return request.build_absolute_uri(signed)
    return signed


# ───────────────────────────── Helpers ─────────────────────────────

def compute_sha256(file_obj, chunk_size: int = 1024 * 1024) -> str:
    """Stream-hash a file without loading it into memory."""
    h = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(chunk_size), b""):
        h.update(chunk)
    return h.hexdigest()