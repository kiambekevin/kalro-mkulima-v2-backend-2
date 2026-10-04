# apps/badges/admin.py
import json

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import Badge, BadgeTemplate, BadgeVerification


@admin.register(BadgeTemplate)
class BadgeTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "display_label",
        "tint_preview",
        "accent_preview",
        "icon",
        "updated_at",
    )
    list_select_related = ("subject",)
    search_fields = ("subject__label", "label", "icon")
    autocomplete_fields = ("subject",)

    # ------------------------------------------------------------------
    # CRITICAL: any name that is NOT a real model field and appears in
    # `fieldsets` MUST be declared here, or Django raises:
    #   FieldError: Unknown field(s) (<name>) specified for <Model>
    # ------------------------------------------------------------------
    readonly_fields = (
        "id",
        "tint_preview",
        "accent_preview",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": ("id", "subject", "label", "icon"),
            },
        ),
        (
            "Visual styling",
            {
                "fields": (
                    ("tint_hex", "tint_preview"),
                    ("accent_hex", "accent_preview"),
                ),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="Tint colour")
    def tint_preview(self, obj):
        # obj is None on the "Add" page — guard against that
        if not obj or not obj.tint_hex:
            return "—"
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'background-color:{0};border:1px solid #ccc;border-radius:3px;'
            'vertical-align:middle;margin-right:6px;"></span>'
            '<code style="vertical-align:middle">{0}</code>',
            obj.tint_hex,
        )

    @admin.display(description="Accent colour")
    def accent_preview(self, obj):
        if not obj or not obj.accent_hex:
            return "—"
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'background-color:{0};border:1px solid #ccc;border-radius:3px;'
            'vertical-align:middle;margin-right:6px;"></span>'
            '<code style="vertical-align:middle">{0}</code>',
            obj.accent_hex,
        )

    @admin.display(description="Label")
    def display_label(self, obj):
        return obj.display_label


class BadgeVerificationInline(admin.TabularInline):
    model = BadgeVerification
    extra = 0
    can_delete = False
    fields = ("verified_at", "verifier_ip", "verifier_ua_short", "verifier_referer")
    readonly_fields = fields
    ordering = ("-verified_at",)
    max_num = 20

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="User agent")
    def verifier_ua_short(self, obj):
        ua = obj.verifier_ua or ""
        return ua[:50] + ("…" if len(ua) > 50 else "")


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = (
        "badge_id",
        "user",
        "course",
        "status_badge",
        "issued_at",
        "expires_at",
        "is_verifiable_flag",
        "has_png",
    )
    list_filter = ("status", "issued_at", "expires_at", "created_at")
    search_fields = (
        "badge_id",
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__phone",
        "course__title",
        "course__slug",
    )
    autocomplete_fields = ("user", "course")
    inlines = (BadgeVerificationInline,)
    date_hierarchy = "issued_at"
    list_select_related = ("user", "course", "course__subject")

    readonly_fields = (
        "id",
        "badge_id",
        "issued_at",
        "is_verifiable_flag",
        "png_preview",
        "snapshot_formatted",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Badge information",
            {
                "fields": ("id", "badge_id", "user", "course", "status", "png_file"),
            },
        ),
        (
            "Lifecycle & verification",
            {
                "fields": (
                    "issued_at",
                    "expires_at",
                    "revoked_at",
                    "is_verifiable_flag",
                ),
            },
        ),
        ("Preview", {"fields": ("png_preview",)}),
        (
            "Metadata snapshot",
            {
                "classes": ("collapse",),
                "fields": ("snapshot_formatted",),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("user", "course", "course__subject")
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colours = {
            Badge.Status.ISSUED: "#23804A",
            Badge.Status.REVOKED: "#C0392B",
            Badge.Status.EXPIRED: "#6c757d",
        }
        colour = colours.get(obj.status, "#000000")
        return format_html(
            '<span style="background-color:{};color:#fff;padding:2px 8px;'
            'border-radius:12px;font-weight:700;font-size:11px;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.display(description="Verifiable", boolean=True)
    def is_verifiable_flag(self, obj):
        return obj.is_verifiable

    @admin.display(description="PNG")
    def has_png(self, obj):
        return "✓" if obj.png_file else "—"

    @admin.display(description="Badge preview")
    def png_preview(self, obj):
        if not obj or not obj.png_file:
            return "PNG not generated yet."
        return format_html(
            '<img src="{}" alt="{}" '
            'style="max-width:240px;border-radius:12px;'
            'box-shadow:0 6px 16px rgba(18,59,38,.2)" />',
            obj.png_file.url,
            obj.badge_id,
        )

    @admin.display(description="Snapshot data")
    def snapshot_formatted(self, obj):
        if not obj or not obj.snapshot:
            return "—"
        return format_html(
            "<pre style='white-space:pre-wrap;font-size:12px'>{}</pre>",
            json.dumps(obj.snapshot, indent=2, ensure_ascii=False),
        )

    @admin.action(description="Revoke selected badges")
    def action_revoke_badges(self, request, queryset):
        count = 0
        for badge in queryset.exclude(status=Badge.Status.REVOKED):
            badge.revoke(reason="Revoked via admin action.")
            count += 1
        self.message_user(request, f"Revoked {count} badge(s).", messages.SUCCESS)

    @admin.action(description="Mark selected badges as expired")
    def action_mark_expired(self, request, queryset):
        updated = queryset.update(
            status=Badge.Status.EXPIRED,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Marked {updated} badge(s) as expired.",
            messages.SUCCESS,
        )

    @admin.action(description="Regenerate PNG for selected badges")
    def action_regenerate_png(self, request, queryset):
        from . import tasks
        count = 0
        for badge in queryset:
            tasks.render_badge_png_task.delay(badge.id, overwrite=True)
            count += 1
        self.message_user(
            request,
            f"Queued PNG regeneration for {count} badge(s).",
            messages.SUCCESS,
        )


@admin.register(BadgeVerification)
class BadgeVerificationAdmin(admin.ModelAdmin):
    list_display = ("badge", "verified_at", "verifier_ip", "verifier_ua_short")
    list_filter = ("verified_at",)
    search_fields = ("badge__badge_id", "verifier_ip", "verifier_ua", "verifier_referer")
    autocomplete_fields = ("badge",)
    date_hierarchy = "verified_at"
    readonly_fields = (
        "id",
        "badge",
        "verifier_ip",
        "verifier_ua",
        "verifier_referer",
        "verified_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="User agent")
    def verifier_ua_short(self, obj):
        ua = obj.verifier_ua or ""
        return ua[:50] + ("…" if len(ua) > 50 else "")