# apps/analytics/serializers.py
from rest_framework import serializers

from .models import VisitEvent


class VisitEventSerializer(serializers.Serializer):
    """
    Payload sent by the frontend when a course or lesson page loads.

      resource_type: "course" | "lesson"
      slug:          the course slug, or (course slug + lesson identifier)
    """
    resource_type = serializers.ChoiceField(
        choices=[VisitEvent.ResourceType.COURSE, VisitEvent.ResourceType.LESSON]
    )
    course_slug = serializers.SlugField(required=False, allow_blank=True)
    lesson_identifier = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        rt = data["resource_type"]
        if rt == VisitEvent.ResourceType.COURSE and not data.get("course_slug"):
            raise serializers.ValidationError(
                {"course_slug": "Required for course visits."}
            )
        if rt == VisitEvent.ResourceType.LESSON and not data.get("lesson_identifier"):
            raise serializers.ValidationError(
                {"lesson_identifier": "Required for lesson visits."}
            )
        return data