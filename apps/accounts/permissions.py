# apps/accounts/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSelfOrAdmin(BasePermission):
    """Object-level: only the owning user or an admin can read/update."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return getattr(obj, "user_id", None) == request.user.id or obj == request.user


class IsTrainer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_trainer


class IsCountyOfficer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_county_officer


class ReadOnlyOrStaff(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff