# api/permissions.py
"""
API-layer permission defaults and shortcuts.
Domain-specific permissions live in each app's `permissions.py`.
"""
from rest_framework.permissions import (  # noqa: F401 — re-exported for convenience
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)

from apps.common.permissions import (  # noqa: F401
    HasRole,
    IsOwner,
    IsOwnerOrStaff,
    IsStaffOrReadOnly,
    ReadOnly,
)

# Convenience subclasses for the API layer

class IsLearner(HasRole):
    allowed_roles = ("farmer", "agripreneur", "extension", "trainer", "student")


class IsTrainerOrAdmin(HasRole):
    allowed_roles = ("trainer", "researcher", "admin")


class IsCountyOfficerOrAdmin(HasRole):
    allowed_roles = ("county", "admin")


# The default permission classes referenced from settings.REST_FRAMEWORK
DEFAULT_PERMISSION_CLASSES = (
    "rest_framework.permissions.IsAuthenticatedOrReadOnly",
)