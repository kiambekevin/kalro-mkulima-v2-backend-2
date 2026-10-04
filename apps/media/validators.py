# apps/media/validators.py
from django.core.exceptions import ValidationError

from .constants import (
    MAX_VIDEO_SIZE_MB,
    MAX_PDF_SIZE_MB,
    MAX_IMAGE_SIZE_MB,
    VIDEO_MIME_TYPES,
    PDF_MIME_TYPES,
    IMAGE_MIME_TYPES,
)


def validate_video_upload(file):
    if file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Video exceeds {MAX_VIDEO_SIZE_MB} MB.")
    if hasattr(file, "content_type") and file.content_type not in VIDEO_MIME_TYPES:
        raise ValidationError(f"Unsupported video type: {file.content_type}")


def validate_pdf_upload(file):
    if file.size > MAX_PDF_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"PDF exceeds {MAX_PDF_SIZE_MB} MB.")
    if hasattr(file, "content_type") and file.content_type not in PDF_MIME_TYPES:
        raise ValidationError("Only PDF files are accepted.")


def validate_image_upload(file):
    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image exceeds {MAX_IMAGE_SIZE_MB} MB.")
    if hasattr(file, "content_type") and file.content_type not in IMAGE_MIME_TYPES:
        raise ValidationError("Only JPEG, PNG or WebP images are accepted.")


def validate_manifest_url(value: str):
    if not value:
        return
    if not value.startswith("https://"):
        raise ValidationError("Manifest URLs must use HTTPS.")
    if not (value.endswith(".m3u8") or value.endswith(".mpd")):
        raise ValidationError("Manifest URLs must end in .m3u8 or .mpd.")