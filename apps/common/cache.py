# apps/common/cache.py
"""
Cache key conventions and tiny decorators for cache-aside reads.

Every cache key in the project should go through `make_key(...)` so we
can invalidate by prefix during deploys and tests.
"""
import functools
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

PREFIX = "kalro"
TTL_SHORT = 60
TTL_MEDIUM = 60 * 5
TTL_LONG = 60 * 30
TTL_DAY = 60 * 60 * 24


def make_key(*parts, version: str = "v1") -> str:
    return ":".join([PREFIX, version, *[str(p) for p in parts if p is not None]])


def cached(key: str, ttl: int = TTL_MEDIUM):
    """
    Decorator that memoises a function's return value in the cache.
    Only positional args are hashed into the key — use `key_builder`
    if you need more control.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            effective = key
            if args or kwargs:
                suffix = "|".join(str(a) for a in args) + "|" + "|".join(
                    f"{k}={v}" for k, v in sorted(kwargs.items())
                )
                effective = f"{key}:{hash(suffix)}"
            hit = cache.get(effective)
            if hit is not None:
                return hit
            value = func(*args, **kwargs)
            cache.set(effective, value, ttl)
            return value
        return wrapper
    return decorator


def invalidate(*parts) -> int:
    """
    Delete a specific cache key. Returns 1 if the key existed, 0 otherwise.
    """
    return 1 if cache.delete(make_key(*parts)) else 0


def invalidate_prefix(prefix: str) -> int:
    """
    Delete every key matching `prefix*`. Uses django-redis's pattern
    delete when available; otherwise it's a no-op with a warning.
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        pattern = make_key(prefix) + "*"
        count = 0
        for key in conn.scan_iter(match=pattern):
            conn.delete(key)
            count += 1
        return count
    except Exception:  # noqa: BLE001
        logger.warning("invalidate_prefix only works with django-redis.")
        return 0