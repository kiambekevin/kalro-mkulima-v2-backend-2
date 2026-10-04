# apps/media/constants.py

# Allowed MIME types & extensions
VIDEO_MIME_TYPES = {
    "video/mp4",
    "application/vnd.apple.mpegurl",     # HLS manifest
    "application/dash+xml",              # DASH manifest
}

PDF_MIME_TYPES = {"application/pdf"}

IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Max sizes
MAX_VIDEO_SIZE_MB = 2000        # 2 GB
MAX_PDF_SIZE_MB = 50
MAX_IMAGE_SIZE_MB = 5

# Signature TTL (seconds)
DEFAULT_SIGNED_URL_TTL = 600    # 10 min
PDF_SIGNED_URL_TTL = 1800       # 30 min

# Processing statuses
STATUS_PENDING = "pending"
STATUS_UPLOADING = "uploading"
STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"

# Upload session lifetime (seconds) — client must finish within this window
UPLOAD_SESSION_TTL = 60 * 60 * 24  # 24 hours