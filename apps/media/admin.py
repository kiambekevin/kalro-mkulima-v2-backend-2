# apps/media/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import MediaAsset, UploadSession
from .services import signed_playback_url, signed_download_url
from . import tasks


class UploadSessionInline(admin.TabularInline):
    model = UploadSession
    extra = 0
    can_delete = False
    readonly_fields = (
        "id", "expected_size", "received_bytes",
        "completed_at", "expires_at", "created_at",
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = (
        "slug", "kind", "status", "title", "size_display",
        "duration_display", "uploaded_by", "created_at",
    )
    list_filter = ("kind", "status", "created_at")
    search_fields = ("slug", "title", "manifest_url", "uploaded_by__email")
    readonly_fields = (
        "id", "slug", "created_at", "updated_at",
        "preview", "playback_url_link", "download_url_link",
    )
    inlines = (UploadSessionInline,)
    date_hierarchy = "created_at"
    actions = ("action_trigger_transcode", "action_mark_ready")

    fieldsets = (
        ("Identity", {"fields": ("id", "slug", "kind", "status", "title", "uploaded_by")}),
        ("File", {"fields": ("file", "mime_type", "size_bytes", "checksum_sha256")}),
        ("Video", {"fields": ("manifest_url", "segments_base_url", "poster_url", "duration_seconds")}),
        ("Dimensions", {"fields": ("width", "height"), "classes": ("collapse",)}),
        ("Preview", {"fields": ("preview", "playback_url_link", "download_url_link")}),
        ("Errors", {"fields": ("error_message",), "classes": ("collapse",)}),
        ("Meta", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Size")
    def size_display(self, obj):
        if not obj.size_bytes:
            return "—"
        mb = obj.size_bytes / (1024 * 1024)
        return f"{mb:.1f} MB"

    @admin.display(description="Duration")
    def duration_display(self, obj):
        if not obj.duration_seconds:
            return "—"
        m, s = divmod(obj.duration_seconds, 60)
        return f"{m}m {s}s"

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.kind == MediaAsset.Kind.IMAGE and obj.file:
            return format_html('<img src="{}" style="max-width:240px;border-radius:10px" />', obj.file.url)
        if obj.kind == MediaAsset.Kind.VIDEO and obj.poster_url:
            return format_html('<img src="{}" style="max-width:240px;border-radius:10px" />', obj.poster_url)
        return "—"

    @admin.display(description="Playback URL (signed)")
    def playback_url_link(self, obj):
        if not obj.pk or obj.kind != MediaAsset.Kind.VIDEO:
            return "—"
        url = signed_playback_url(obj)
        return format_html('<a href="{}" target="_blank" rel="noreferrer">{}</a>', url, url)

    @admin.display(description="Download URL (signed)")
    def download_url_link(self, obj):
        if not obj.pk or not obj.file:
            return "—"
        url = signed_download_url(obj)
        return format_html('<a href="{}" target="_blank" rel="noreferrer">{}</a>', url, url)

    @admin.action(description="Trigger transcode for selected videos")
    def action_trigger_transcode(self, request, queryset):
        count = 0
        for asset in queryset.filter(kind=MediaAsset.Kind.VIDEO):
            tasks.trigger_transcode.delay(asset.id)
            count += 1
        self.message_user(request, f"Queued transcode for {count} video(s).")

    @admin.action(description="Mark selected as ready")
    def action_mark_ready(self, request, queryset):
        count = queryset.update(status="ready")
        self.message_user(request, f"Marked {count} asset(s) as ready.")


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "asset", "user", "percent", "is_expired", "completed_at", "created_at")
    list_filter = ("completed_at",)
    search_fields = ("asset__slug", "user__email")
    readonly_fields = (
        "id", "asset", "user", "expected_size", "received_bytes",
        "upload_url", "upload_fields", "completed_at", "expires_at", "created_at",
    )

    def has_add_permission(self, request):
        return False