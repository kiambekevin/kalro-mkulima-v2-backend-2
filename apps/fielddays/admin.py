# apps/fielddays/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import FieldDay, Booking, Attendance


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ("user", "code", "status", "booked_at", "cancelled_at")
    readonly_fields = ("code", "booked_at")
    raw_id_fields = ("user",)
    ordering = ("booked_at",)
    show_change_link = True


@admin.register(FieldDay)
class FieldDayAdmin(admin.ModelAdmin):
    list_display = (
        "title", "county", "topic", "starts_at", "spots",
        "booked_display", "status", "host",
    )
    list_filter = ("status", "county", "topic", "starts_at")
    search_fields = ("title", "venue", "host", "slug")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("county", "topic", "host_user")
    inlines = (BookingInline,)
    date_hierarchy = "starts_at"
    readonly_fields = (
        "booked_display", "attended_display", "waitlisted_display",
        "created_at", "updated_at",
    )
    actions = ("action_publish", "action_cancel")

    fieldsets = (
        ("Identity", {"fields": ("slug", "title", "description", "topic")}),
        ("Location", {"fields": ("county", "venue", "latitude", "longitude")}),
        ("Time", {"fields": ("starts_at", "ends_at", "timezone_name")}),
        ("Capacity", {"fields": ("spots", "waitlist_enabled")}),
        ("Host", {"fields": ("host", "host_user", "contact_phone", "contact_email")}),
        ("Media", {"fields": ("cover_image_url",)}),
        ("Publishing", {"fields": ("status", "notes")}),
        ("Stats", {"fields": ("booked_display", "attended_display", "waitlisted_display")}),
        ("Meta", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Booked")
    def booked_display(self, obj):
        return f"{obj.booked_count}/{obj.spots}"

    @admin.display(description="Attended")
    def attended_display(self, obj):
        return obj.attended_count

    @admin.display(description="Waitlisted")
    def waitlisted_display(self, obj):
        return obj.waitlisted_count

    @admin.action(description="Publish selected field days")
    def action_publish(self, request, queryset):
        count = queryset.update(status="published")
        self.message_user(request, f"Published {count} field day(s).")

    @admin.action(description="Cancel selected field days")
    def action_cancel(self, request, queryset):
        count = 0
        for fd in queryset:
            fd.cancel(reason="Bulk cancel via admin")
            count += 1
        self.message_user(request, f"Cancelled {count} field day(s).")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "code", "user", "field_day", "status",
        "booked_at", "attended_display",
    )
    list_filter = ("status", "field_day__county", "field_day__topic")
    search_fields = ("code", "user__email", "user__phone", "field_day__title")
    autocomplete_fields = ("user", "field_day")
    readonly_fields = ("code", "booked_at", "cancelled_at")
    date_hierarchy = "booked_at"

    @admin.display(description="Attended")
    def attended_display(self, obj):
        return "✓" if hasattr(obj, "attendance") else "—"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "booking_code", "user", "field_day", "checked_in_at", "checked_in_by",
    )
    list_filter = ("checked_in_at", "booking__field_day__county")
    search_fields = ("booking__code", "booking__user__email", "booking__field_day__title")
    readonly_fields = (
        "booking", "checked_in_at", "checked_in_by",
        "latitude", "longitude", "notes",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Booking code")
    def booking_code(self, obj):
        return obj.booking.code

    @admin.display(description="User")
    def user(self, obj):
        return obj.booking.user.email

    @admin.display(description="Field day")
    def field_day(self, obj):
        return obj.booking.field_day.title