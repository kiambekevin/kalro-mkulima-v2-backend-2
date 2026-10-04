# apps/dashboard/cache.py
"""
Cache keys + invalidation helpers specific to the dashboard.

Learner dashboards are cached per user, county dashboards per county.
Every write from other apps (progress, badges, fielddays) should call
the appropriate invalidation helper.
"""
from django.core.cache import cache

from apps.common.cache import make_key
from .constants import LEARNER_DASHBOARD_TTL, COUNTY_DASHBOARD_TTL


# ───────────────────────────── Keys ─────────────────────────────

def learner_key(user_id) -> str:
    return make_key("dashboard", "learner", str(user_id))


def county_key(county_id) -> str:
    return make_key("dashboard", "county", str(county_id))


# ───────────────────────────── Read/write ─────────────────────────────

def get_learner_dashboard(user_id):
    return cache.get(learner_key(user_id))


def set_learner_dashboard(user_id, payload, ttl: int = LEARNER_DASHBOARD_TTL):
    cache.set(learner_key(user_id), payload, ttl)


def get_county_dashboard(county_id):
    return cache.get(county_key(county_id))


def set_county_dashboard(county_id, payload, ttl: int = COUNTY_DASHBOARD_TTL):
    cache.set(county_key(county_id), payload, ttl)


# ───────────────────────────── Invalidation ─────────────────────────────

def invalidate_learner(user_id) -> None:
    cache.delete(learner_key(user_id))


def invalidate_county(county_id) -> None:
    cache.delete(county_key(county_id))


def invalidate_all() -> int:
    """
    Clear every cached dashboard. Uses django-redis's pattern delete
    when available; otherwise it's a no-op with a warning.
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        pattern = make_key("dashboard") + "*"
        count = 0
        for key in conn.scan_iter(match=pattern):
            conn.delete(key)
            count += 1
        return count
    except Exception:  # noqa: BLE001
        return 0