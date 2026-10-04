# apps/badges/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsBadgeOwnerOrAdmin(BasePermission):
    """Wallet items — only the owner or an admin can see them."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user_id == request.user.id


class IsAdminOrTemplateEditor(BasePermission):
    """
    Templates and manual issuance — admin only. Read is public so the
    React app can fetch the colour palette for each subject.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff