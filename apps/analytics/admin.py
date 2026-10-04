# apps/analytics/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import DailyVisitRollup, VisitEvent


@admin.register(VisitEvent)
class VisitEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "resource_type", "course", "lesson",
        "user", "county", "ip_address",
    )
    list_filter = ("resource_type", "county", "created_at")
    search_fields = (
        "course__title", "lesson__title",
        "user__email", "session_id", "ip_address",
    )
    date_hierarchy = "created_at"
    readonly_fields = (
        "id", "user", "session_id", "ip_address", "user_agent",
        "resource_type", "course", "lesson", "county", "created_at",
    )
    list_select_related = ("course", "lesson", "user", "county")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # append-only audit table


@admin.register(DailyVisitRollup)
class DailyVisitRollupAdmin(admin.ModelAdmin):
    list_display = ("date", "resource_type", "course", "lesson", "county", "count")
    list_filter = ("resource_type", "date", "county")
    date_hierarchy = "date"