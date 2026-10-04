# apps/common/admin.py
"""
Shared admin helpers — imported by other apps' `admin.py`.
"""
from django.contrib import admin


class ReadOnlyAdminMixin:
    """
    Disables add / change / delete for a ModelAdmin. Useful for audit
    models like BadgeVerification, RequestLog, etc.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TimestampAdminMixin:
    """
    Shows `created_at` and `updated_at` as read-only and adds them to
    list_filter. Only use on models that inherit TimeStampedModel.
    """
    timestamp_readonly = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        existing = super().get_readonly_fields(request, obj)
        return existing + tuple(
            f for f in self.timestamp_readonly
            if hasattr(self.model, f) and f not in existing
        )

    def get_list_filter(self, request):
        existing = super().get_list_filter(request)
        return existing + tuple(
            f for f in self.timestamp_readonly
            if hasattr(self.model, f) and f not in existing
        )


class SlugAdminMixin:
    """
    Auto-fills `slug` from a source field in the admin form.
    """
    slug_source_field = "title"
    prepopulated_fields = {}  # set in subclasses via `get_prepopulated_fields`

    def get_prepopulated_fields(self, request, obj=None):
        existing = dict(super().get_prepopulated_fields(request, obj))
        if hasattr(self.model, "slug"):
            existing.setdefault("slug", (self.slug_source_field,))
        return existing