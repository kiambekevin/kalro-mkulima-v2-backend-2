from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Course, Lesson, Module, Resource, Subject, Pathway, PathwayCourse

# ───────────────────────────── Subject ─────────────────────────────

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("label", "slug", "icon", "order", "course_count")
    list_editable = ("order",)
    search_fields = ("label", "slug")
    prepopulated_fields = {"slug": ("label",)}
    ordering = ("order", "label")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("slug", "label", "icon", "description", "order"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _course_count=Count("courses", distinct=True)
        )

    @admin.display(description="Courses", ordering="_course_count")
    def course_count(self, obj):
        return obj._course_count


# ───────────────────────────── Module inline on Course ─────────────────────────────

class ModuleInline(admin.StackedInline):
    model = Module
    extra = 0
    fields = ("title", "summary", "order")
    ordering = ("order",)
    show_change_link = True


# ───────────────────────────── Course ─────────────────────────────

# apps/courses/admin.py

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title", "subject", "level", "hours",
        "rating", "popular", "is_published", "published_at",
    )
    list_filter = ("subject", "level", "is_published", "popular", "badge_enabled")
    search_fields = ("title", "slug", "summary")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("popular", "is_published")
    autocomplete_fields = ("subject", "instructor")
    inlines = (ModuleInline,)
    date_hierarchy = "published_at"
    list_select_related = ("subject", "instructor")

    # Define main fieldsets
    fieldsets = (
        ("Identity", {
            "fields": (
                "slug",
                "title",
                "summary",
                "description",
            ),
        }),
        ("Taxonomy", {
            "fields": (
                "subject",
                "level",
                "hours",
                "rating",
                "review_count",
            ),
        }),
        ("Author", {
            "fields": ("instructor",),
        }),
        ("Badge", {
            "fields": ("badge_enabled",),
        }),
        ("Media", {
            "fields": ("image_url", "alt_text"),
        }),
        ("Publishing", {
            "fields": ("is_published", "published_at", "popular"),
        }),
        ("Source data", {
            "classes": ("collapse",),
            "fields": ("updated_source_date",),
        }),
        ("Meta", {
            "classes": ("collapse",),
            "fields": ("lesson_count_link", "created_at", "updated_at"),
        }),
    )

    # Alias add_fieldsets to fieldsets so custom base classes/mixins find it
    add_fieldsets = fieldsets

    def get_fieldsets(self, request, obj=None):
        """Ensure fieldsets are always returned for both Add (obj=None) and Change forms."""
        if not obj and hasattr(self, "add_fieldsets") and self.add_fieldsets:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = ["lesson_count_link", "created_at", "updated_at"]
        if obj:  # Read-only ONLY when editing an existing record
            readonly.append("published_at")
        return readonly

    @admin.display(description="Lessons")
    def lesson_count_link(self, obj):
        if not obj or not obj.pk:
            return "—"
        count = obj.lessons.count()
        url = f"/admin/courses/lesson/?module__course__id__exact={obj.pk}"
        return format_html('<a href="{}">{} lesson(s)</a>', url, count)

# ───────────────────────────── Resource inline on Lesson ─────────────────────────────

class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 0
    fields = (
        "kind", "title", "publisher", "url", "file",
        "size_label", "category", "order",
    )
    ordering = ("order",)
    show_change_link = True


# ───────────────────────────── Module ─────────────────────────────

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "lesson_count")
    list_filter = ("course__subject",)
    search_fields = ("title", "course__title")
    autocomplete_fields = ("course",)
    ordering = ("course", "order")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("course",)

    fieldsets = (
        (None, {
            "fields": ("course", "title", "summary", "order"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _lesson_count=Count("lessons", distinct=True)
        )

    @admin.display(description="Lessons", ordering="_lesson_count")
    def lesson_count(self, obj):
        return obj._lesson_count


# ───────────────────────────── Lesson ─────────────────────────────

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title", "module", "course_display", "type",
        "minutes", "order", "is_preview", "resource_count",
    )
    list_filter = ("type", "is_preview", "module__course__subject")
    search_fields = ("title", "slug", "body", "module__title", "module__course__title")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("module",)
    inlines = (ResourceInline,)
    ordering = ("module__course", "module__order", "order")
    list_select_related = ("module", "module__course")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Identity", {
            "fields": (
                "module",
                "slug",
                "title",
                "order",
            ),
        }),
        ("Content", {
            "fields": (
                "type",
                "minutes",
                "is_preview",
                "body",
            ),
        }),
        ("Media", {
            "fields": (
                "stream_url",
                "poster_url",
                "resource_file",
                "resource_label",
            ),
        }),
        ("Notes", {
            "classes": ("collapse",),
            "fields": ("notes",),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _resource_count=Count("resources", distinct=True)
        )

    @admin.display(description="Course", ordering="module__course__title")
    def course_display(self, obj):
        return obj.module.course.title

    @admin.display(description="Resources", ordering="_resource_count")
    def resource_count(self, obj):
        return obj._resource_count


# ───────────────────────────── Resource ─────────────────────────────

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title", "kind", "publisher",
        "lesson", "category", "order",
    )
    list_filter = ("kind", "category")
    search_fields = ("title", "publisher", "lesson__title")
    autocomplete_fields = ("lesson",)
    ordering = ("lesson", "order")
    list_select_related = ("lesson",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Identity", {
            "fields": ("lesson", "kind", "title", "publisher"),
        }),
        ("Content", {
            "fields": ("description", "url", "file"),
        }),
        ("Presentation", {
            "fields": ("size_label", "category", "order"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )


class PathwayCourseInline(admin.TabularInline):
    model = PathwayCourse
    extra = 1
    autocomplete_fields = ("course",)
    fields = ("order", "course")
    ordering = ("order",)


@admin.register(Pathway)
class PathwayAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "course_count_display", "badge_label", "is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("title", "slug", "summary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (PathwayCourseInline,)
    ordering = ("order", "title")

    @admin.display(description="Courses")
    def course_count_display(self, obj):
        return obj.course_count
