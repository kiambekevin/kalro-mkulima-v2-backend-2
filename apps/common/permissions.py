# apps/common/permissions.py
"""
Base permission classes reused across apps. Domain-specific
permissions live in each app's own `permissions.py`.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ReadOnly(BasePermission):
    """Only allow safe methods."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsOwner(BasePermission):
    """
    Object-level check: the object's `user` (or the object itself, if it
    *is* a user) must match `request.user`.
    """

    def has_object_permission(self, request, view, obj):
        return (
            getattr(obj, "user_id", None) == request.user.id
            or getattr(obj, "user", None) == request.user
            or obj == request.user
        )


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff


class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return getattr(obj, "user_id", None) == request.user.id


class HasRole(BasePermission):
    """
    Base class for role-based permissions. Subclasses set `allowed_roles`.

    Usage:
        class IsTrainer(HasRole):
            allowed_roles = ("trainer", "admin")
    """
    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return getattr(request.user, "role", None) in self.allowed_roles