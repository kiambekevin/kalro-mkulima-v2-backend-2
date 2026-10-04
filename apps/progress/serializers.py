# apps/progress/serializers.py
from rest_framework import serializers

from .models import CourseProgress, LessonCompletion, DailyActivity


class CourseProgressSerializer(serializers.ModelSerializer):
    """Full progress payload for a single course."""
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_image = serializers.CharField(source="course.image", read_only=True)
    subject = serializers.CharField(source="course.subject.slug", read_only=True)
    subject_label = serializers.CharField(source="course.subject.label", read_only=True)
    level = serializers.CharField(source="course.level", read_only=True)
    hours = serializers.IntegerField(source="course.hours", read_only=True)
    last_lesson_id = serializers.UUIDField(read_only=True)
    last_lesson_slug = serializers.CharField(
        source="last_lesson.slug", read_only=True, allow_null=True
    )

    class Meta:
        model = CourseProgress
        fields = [
            "id",
            "course_slug", "course_title", "course_image",
            "subject", "subject_label", "level", "hours",
            "completed_count", "total_count", "percent",
            "last_lesson_id", "last_lesson_slug",
            "last_seen_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class LessonCompletionSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    lesson_slug = serializers.CharField(source="lesson.slug", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)

    class Meta:
        model = LessonCompletion
        fields = [
            "id",
            "lesson", "lesson_title", "lesson_slug",
            "course", "course_slug",
            "completed_at",
        ]
        read_only_fields = fields


class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = ["date", "lessons_completed", "minutes_spent", "courses_touched"]


class CompleteLessonSerializer(serializers.Serializer):
    """
    Payload for POST /progress/lessons/{lesson_id}/complete/
    Optional fields let the client pass location or timing hints.
    """
    minutes_spent = serializers.IntegerField(
        required=False, min_value=0, max_value=240, default=0,
    )


class ToggleLessonSerializer(serializers.Serializer):
    """
    Payload for POST /progress/lessons/{lesson_id}/toggle/
    """
    force = serializers.BooleanField(default=False)


class UpdateLastLessonSerializer(serializers.Serializer):
    """
    Payload for POST /progress/courses/{slug}/last-lesson/
    Called by the lesson viewer on every lesson load so the dashboard
    knows where to send the learner back.
    """
    lesson_id = serializers.UUIDField()


class StreakSerializer(serializers.Serializer):
    """Response shape for /progress/streak/."""
    current = serializers.IntegerField()
    longest = serializers.IntegerField()
    last_active_date = serializers.DateField(allow_null=True)
    active_today = serializers.BooleanField()