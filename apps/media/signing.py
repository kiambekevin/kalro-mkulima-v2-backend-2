# apps/media/signing.py
"""
Signed URLs for media access.

Videos and PDFs are served by the CDN / S3, not by Django. This module
generates short-lived signed URLs so:

  - the client (React + Shaka Player) can stream videos directly
  - the client can download PDFs for offline use
  - the URL expires, so a shared link doesn't leak forever

The signature is HMAC-SHA256 over (path + expiry + client_id),
with a key from settings.MEDIA_SIGNING_KEY.
"""
import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _signing_key() -> bytes:
    key = getattr(settings, "MEDIA_SIGNING_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "MEDIA_SIGNING_KEY must be set to sign media URLs."
        )
    return key.encode("utf-8")


def _sign(payload: str) -> str:
    digest = hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def sign_url(base_url: str, ttl: int = 600, extra: dict | None = None) -> str:
    """
    Append `expires` and `sig` query parameters to a URL.

    `extra` is merged into the signed payload so callers can bind a URL
    to a specific user or role without exposing those values in a
    forgeable way.
    """
    if not base_url:
        return ""

    expires = int(time.time()) + ttl
    params = {"expires": expires}
    if extra:
        params.update({k: str(v) for k, v in extra.items()})

    payload = base_url + "?" + urlencode(sorted(params.items()))
    signature = _sign(payload)

    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query))
    query.update(params)
    query["sig"] = signature

    return urlunparse(parsed._replace(query=urlencode(query)))


def verify_signed_url(url: str) -> bool:
    """Returns True if `url` carries a valid, unexpired signature."""
    if not url:
        return False

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))

    signature = query.pop("sig", None)
    if not signature:
        return False

    try:
        expires = int(query.get("expires", "0"))
    except ValueError:
        return False

    if expires < int(time.time()):
        return False

    base = urlunparse(parsed._replace(query=""))
    payload = base + "?" + urlencode(sorted(query.items()))
    expected = _sign(payload)

    return hmac.compare_digest(signature, expected)


def strip_query(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query=""))