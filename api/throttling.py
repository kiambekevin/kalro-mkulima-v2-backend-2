# api/throttling.py
"""
Rate limiting classes. Attach via `throttle_classes` on views, or set
scoped defaults in settings.

    REST_FRAMEWORK = {
        "DEFAULT_THROTTLE_CLASSES": ("api.throttling.AnonBurstThrottle", ...),
        "DEFAULT_THROTTLE_RATES": {
            "anon": "60/min",
            "user": "600/min",
            "auth": "10/min",
            "verify": "60/min",
            "upload": "10/hour",
        },
    }
"""
from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class AnonBurstThrottle(AnonRateThrottle):
    scope = "anon"


class UserSustainedThrottle(UserRateThrottle):
    scope = "user"


class AuthThrottle(SimpleRateThrottle):
    """
    Stricter limit for login / register / password reset.
    Keyed by IP so an attacker can't brute-force by rotating emails.
    """
    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class BadgeVerifyThrottle(SimpleRateThrottle):
    """
    Public badge verification is cheap but heavily scanned by bots;
    cap it per IP.
    """
    scope = "verify"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class UploadThrottle(UserRateThrottle):
    """
    Media uploads are expensive; cap per authenticated user.
    """
    scope = "upload"


class ScopedUserThrottle(ScopedRateThrottle):
    """
    Generic scoped throttle — set `throttle_scope = "..."` on the view
    and add a rate under `DEFAULT_THROTTLE_RATES` in settings.
    """