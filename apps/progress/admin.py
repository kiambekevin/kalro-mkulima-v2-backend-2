# apps/progress/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import CourseProgress, LessonCompletion, DailyActivity
from .services import rebuild_course_progress


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user", "course_title", "percent_display",
        "completed_count", "total_count",
        "last_seen_at", "updated_at",
    )
    list_filter = ("course__subject", "course__level")
    search_fields = ("user__email", "user__phone", "course__title", "course__slug")
    autocomplete_fields = ("user", "course", "last_lesson")
    readonly_fields = ("created_at", "updated_at", "percent_display")
    date_hierarchy = "updated_at"
    actions = ("action_rebuild",)

    @admin.display(description="Course")
    def course_title(self, obj):
        return obj.course.title

    @admin.display(description="Progress")
    def percent_display(self, obj):
        colour = "#2F9A5A" if obj.percent >= 100 else "#F0B429" if obj.percent > 0 else "#CBD6C9"
        return format_html(
            '<span style="display:inline-block;min-width:44px;text-align:center;'
            'padding:3px 8px;border-radius:999px;color:#fff;font-weight:700;'
            'background:{}">{}</span>',
            colour, f"{obj.percent}%",
        )

    @admin.action(description="Rebuild progress for selected rows")
    def action_rebuild(self, request, queryset):
        count = 0
        for cp in queryset:
            rebuild_course_progress(cp.user, cp.course)
            count += 1
        self.message_user(request, f"Rebuilt {count} CourseProgress row(s).")


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson_title", "course_title", "completed_at")
    list_filter = ("course__subject", "completed_at")
    search_fields = ("user__email", "user__phone", "lesson__title", "course__title")
    autocomplete_fields = ("user", "lesson", "course")
    date_hierarchy = "completed_at"
    readonly_fields = ("completed_at",)

    @admin.display(description="Lesson")
    def lesson_title(self, obj):
        return obj.lesson.title

    @admin.display(description="Course")
    def course_title(self, obj):
        return obj.course.title


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = (
        "user", "date", "lessons_completed",
        "minutes_spent", "courses_touched", "updated_at",
    )
    list_filter = ("date",)
    search_fields = ("user__email", "user__phone")
    autocomplete_fields = ("user",)
    date_hierarchy = "date"
    readonly_fields = ("updated_at",)