# apps/fielddays/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class CanManageFieldDay(BasePermission):
    """
    Only county officers, trainers and admins can create or edit events.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user.role in ("county", "trainer", "extension")


class IsHostOrAdmin(BasePermission):
    """
    Object-level: only the host user or an admin can edit an event.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.host_user_id == request.user.id


class CanCheckIn(BasePermission):
    """
    Check-in is performed by county officers, trainers, or the event host.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user.role in ("county", "trainer", "extension")


class IsBookingOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user_id == request.user.id