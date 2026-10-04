# apps/courses/validators.py
"""
Reusable validators for the courses app.

Kept stateless so they can be called from models, serializers, and
management commands alike.
"""
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError


# ───────────────────────────── Constants ─────────────────────────────

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
}

# YouTube video IDs are always 11 characters: A-Z, a-z, 0-9, _, -
YOUTUBE_ID_RE = re.compile(
    r"(?:"
    r"youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|"
    r"youtu\.be/"
    r")([A-Za-z0-9_-]{11})"
)

# Direct video file extensions a native <video> element can play
DIRECT_VIDEO_SUFFIXES = (".mp4", ".webm", ".ogg", ".m4v", ".mov")

# Manifest extensions for adaptive streaming
MANIFEST_SUFFIXES = (".m3u8", ".mpd")


# ───────────────────────────── Numbers ─────────────────────────────

def validate_positive_minutes(value):
    if value is None:
        return
    if value < 1 or value > 240:
        raise ValidationError("Lesson duration must be between 1 and 240 minutes.")


def validate_spots(value):
    if value is None:
        return
    if value < 1 or value > 5000:
        raise ValidationError("Spots must be between 1 and 5000.")


def validate_hex_colour(value):
    if not value:
        return
    if not value.startswith("#") or len(value) not in (4, 7):
        raise ValidationError("Enter a hex colour like #123B26 or #ABC.")


# ───────────────────────────── YouTube ─────────────────────────────

def is_youtube_url(url: str) -> bool:
    """
    True when the URL points at YouTube (any of the standard hosts).
    """
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in YOUTUBE_HOSTS


def extract_youtube_id(url: str) -> str | None:
    """
    Return the 11-character YouTube video ID from any of the standard
    URL shapes, or None:

        https://www.youtube.com/watch?v=dQw4w9WgXcQ
        https://youtu.be/dQw4w9WgXcQ
        https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=share
        https://www.youtube.com/embed/dQw4w9WgXcQ
        https://www.youtube.com/shorts/dQw4w9WgXcQ
        https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ
    """
    if not url:
        return None
    match = YOUTUBE_ID_RE.search(url)
    return match.group(1) if match else None


# ───────────────────────────── Lesson media ─────────────────────────────

def classify_media_url(url: str) -> str | None:
    """
    Classify a URL as one of:

        "youtube"    → YouTube link
        "hls"        → .m3u8 manifest
        "dash"       → .mpd manifest
        "video"      → direct video file (.mp4, .webm, …)
        None         → not a media URL
    """
    if not url:
        return None

    if is_youtube_url(url):
        return "youtube" if extract_youtube_id(url) else None

    lowered = url.lower().split("?", 1)[0].split("#", 1)[0]

    if lowered.endswith(".m3u8"):
        return "hls"
    if lowered.endswith(".mpd"):
        return "dash"
    if lowered.endswith(DIRECT_VIDEO_SUFFIXES):
        return "video"

    return None


def validate_lesson_stream_url(value: str):
    """
    Accept:
      - YouTube URLs (any standard form)
      - HLS manifests      (.m3u8)
      - DASH manifests     (.mpd)
      - direct video files (.mp4, .webm, .ogg, .m4v, .mov)

    In production (`DEBUG=False`), require HTTPS.
    """
    if not value:
        return

    # Protocol check
    if value.startswith("http://") and not getattr(settings, "DEBUG", False):
        raise ValidationError("Stream URLs must use HTTPS in production.")
    if not (value.startswith("https://") or value.startswith("http://")):
        raise ValidationError(
            "Stream URLs must start with http:// or https://."
        )

    # YouTube
    if is_youtube_url(value):
        if not extract_youtube_id(value):
            raise ValidationError(
                "This looks like a YouTube link, but the video ID couldn't "
                "be parsed. Paste the full watch URL or the short youtu.be URL."
            )
        return

    # Everything else must end in a known extension
    lowered = value.lower().split("?", 1)[0].split("#", 1)[0]
    if not lowered.endswith(MANIFEST_SUFFIXES + DIRECT_VIDEO_SUFFIXES):
        raise ValidationError(
            "Stream URL must end in .m3u8 (HLS), .mpd (DASH), "
            ".mp4, .webm, .ogg, .m4v, or be a YouTube link."
        )


def validate_resource_media_url(value: str):
    """
    Lighter validation for a lesson's `resource_file`: any URL is fine
    as long as it looks like a valid https:// URL.
    """
    if not value:
        return
    if not (value.startswith("https://") or value.startswith("http://")):
        raise ValidationError("Resource URLs must start with http(s)://.")