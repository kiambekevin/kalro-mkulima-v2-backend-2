# apps/progress/permissions.py
from rest_framework.permissions import BasePermission


class IsProgressOwner(BasePermission):
    """
    Object-level: only the owner can read or modify their progress.
    Admins can view any user's progress but do not modify it via the
    learner endpoints (they use the admin site instead).
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user_id == request.user.id