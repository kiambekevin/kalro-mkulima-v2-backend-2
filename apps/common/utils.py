# apps/common/utils.py
"""
Small, stateless helpers used in many places. Nothing here touches the
database beyond reading a model instance.
"""
import hashlib
import re
import unicodedata
from typing import Iterable
from uuid import uuid4

from django.db import transaction
from django.utils.text import slugify as django_slugify


# ────────────────────────────── Slugs ──────────────────────────────

def slugify(value: str, *, allow_unicode: bool = False) -> str:
    """Django's slugify, trimmed and normalised."""
    return django_slugify(value or "", allow_unicode=allow_unicode).strip("-")


def unique_slug(instance, value: str, *, field: str = "slug",
                max_length: int = 80) -> str:
    """
    Build a slug that's unique for `instance`'s model, appending a short
    suffix if needed.

        unique_slug(course, "Dairy Farming 101")
        → "dairy-farming-101"
        → "dairy-farming-101-4f7a"  (if already taken)
    """
    base = slugify(value)[:max_length] or uuid4().hex[:8]
    Model = instance.__class__
    slug = base
    suffix = 1
    queryset = Model.objects_all if hasattr(Model, "objects_all") else Model.objects

    while queryset.filter(**{field: slug}).exclude(pk=instance.pk).exists():
        suffix += 1
        tail = f"-{suffix}" if suffix < 1000 else f"-{uuid4().hex[:4]}"
        slug = (base[: max_length - len(tail)] + tail).strip("-")

    return slug


# ────────────────────────────── Hashing ──────────────────────────────

def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def short_hash(value: str | bytes, length: int = 8) -> str:
    return sha256_hex(value)[:length]


# ────────────────────────────── Text ──────────────────────────────

def normalise_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def strip_diacritics(text: str) -> str:
    """Convert accented characters to their ASCII counterparts."""
    if not text:
        return ""
    normalised = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalised if not unicodedata.combining(c))


def truncate(text: str, length: int = 120, ellipsis: str = "…") -> str:
    if text is None:
        return ""
    text = str(text)
    if len(text) <= length:
        return text
    return text[: length - len(ellipsis)].rstrip() + ellipsis


def initials(*parts: str) -> str:
    """'Wanjiku', 'Muthoni' → 'WM'. Empty parts are ignored."""
    letters = [p.strip()[0] for p in parts if p and p.strip()]
    return "".join(letters[:2]).upper() or "?"


# ────────────────────────────── Iterables ──────────────────────────────

def chunked(iterable: Iterable, size: int):
    """Yield successive lists of `size` from iterable."""
    bucket = []
    for item in iterable:
        bucket.append(item)
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


def dedupe_preserve_order(items: Iterable):
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


# ────────────────────────────── Transactions ──────────────────────────────

def atomic(func=None, *, using=None, savepoint=True):
    """
    Alias for django.db.transaction.atomic so callers don't have to
    import it directly. Useful in services modules.
    """
    return transaction.atomic(using=using, savepoint=savepoint)(func)