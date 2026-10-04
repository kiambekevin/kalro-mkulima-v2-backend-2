# apps/media/tasks.py
"""
Background jobs for media: cleanup, transcode-trigger, integrity checks.
"""
import logging

from celery import shared_task

from .constants import STATUS_FAILED, STATUS_READY
from .models import MediaAsset, UploadSession
from .selectors import expired_upload_sessions

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_upload_sessions():
    """Delete upload sessions that were never completed within their TTL."""
    count = expired_upload_sessions().delete()[0]
    logger.info("Cleaned up %d expired upload session(s).", count)
    return count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def trigger_transcode(self, asset_id):
    """
    Kick off HLS transcoding for an uploaded video.

    In production this typically calls a transcoding service (Cloudflare
    Stream, Mux, AWS MediaConvert, or a self-hosted ffmpeg worker). When
    it finishes, the service calls back to `attach_manifest()`.
    """
    try:
        asset = MediaAsset.objects.get(id=asset_id, kind=MediaAsset.Kind.VIDEO)
    except MediaAsset.DoesNotExist:
        return

    if asset.status == STATUS_READY:
        return

    # Placeholder — replace with the real transcoder integration.
    logger.info("Transcode requested for asset %s (%s)", asset.slug, asset.manifest_url)
    # Example (Cloudflare Stream):
    # stream.upload(asset.file, meta={"lesson": asset.slug})
    # then the webhook → attach_manifest_task


@shared_task
def attach_manifest_task(asset_id, manifest_url, segments_base_url="",
                         duration_seconds=None, poster_url=""):
    """Called from a transcoder webhook or the admin action."""
    from .services import attach_manifest
    try:
        asset = MediaAsset.objects.get(id=asset_id)
    except MediaAsset.DoesNotExist:
        logger.warning("attach_manifest_task: asset %s not found.", asset_id)
        return
    attach_manifest(
        asset=asset,
        manifest_url=manifest_url,
        segments_base_url=segments_base_url,
        duration_seconds=duration_seconds,
        poster_url=poster_url,
    )


@shared_task
def verify_asset_integrity(asset_id, expected_checksum):
    """Optionally re-hash a stored file and compare to the recorded checksum."""
    from .services import compute_sha256

    try:
        asset = MediaAsset.objects.get(id=asset_id)
    except MediaAsset.DoesNotExist:
        return

    if not asset.file:
        return

    asset.file.open("rb")
    actual = compute_sha256(asset.file)
    if actual != expected_checksum:
        asset.mark_failed("Checksum mismatch after storage.")
        logger.error("Checksum mismatch for asset %s", asset.slug)