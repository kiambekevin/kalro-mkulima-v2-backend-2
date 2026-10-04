# apps/media/storage.py
"""
Thin wrapper around Django's storage backends.

The rest of the codebase never touches S3 or the local filesystem
directly — everything goes through these two helpers so switching
providers is a one-file change.
"""
from django.conf import settings
from django.core.files.storage import default_storage, storages


def media_storage():
    """
    The default storage for uploads (S3 in prod, filesystem in dev).
    Provided by settings.STORAGES["default"].
    """
    return default_storage


def private_storage():
    """
    Separate storage for private / signed content (videos, paid PDFs).
    Configured via settings.STORAGES["private"] if present, otherwise
    falls back to the default.
    """
    try:
        return storages["private"]
    except KeyError:
        return default_storage


def public_url(path: str) -> str:
    """Unsigned, public URL — for thumbnails, posters, etc."""
    if not path:
        return ""
    return media_storage().url(path)


def exists(path: str) -> bool:
    return media_storage().exists(path) if path else False


def delete(path: str) -> None:
    if path and media_storage().exists(path):
        media_storage().delete(path)