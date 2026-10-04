# apps/dashboard/permissions.py
from rest_framework.permissions import BasePermission

from .constants import COUNTY_DASHBOARD_ROLES


class CanViewCountyDashboard(BasePermission):
    """
    Only county officers and admins can see aggregate data for a county.
    A county officer may only see their own county unless they're staff.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return getattr(user, "role", None) in COUNTY_DASHBOARD_ROLES

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        county_id = getattr(obj, "id", None) or obj
        user_county = getattr(getattr(user, "profile", None), "county_id", None)
        return user_county == county_id