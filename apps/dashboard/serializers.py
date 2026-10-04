# apps/dashboard/serializers.py
"""
Serializers for the dashboard endpoints.

These mostly validate the query parameters and document the response
shape for OpenAPI. The heavy lifting happens in services/selectors.
"""
from rest_framework import serializers


class DashboardQuerySerializer(serializers.Serializer):
    """Query params accepted by GET /api/v1/dashboard/."""
    refresh = serializers.BooleanField(default=False, required=False)


class CountyDashboardQuerySerializer(serializers.Serializer):
    refresh = serializers.BooleanField(default=False, required=False)
    weeks = serializers.IntegerField(min_value=4, max_value=52, default=8, required=False)


# ── Response serializers (used for OpenAPI documentation) ──

class DashboardUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    firstName = serializers.CharField(allow_blank=True)
    lastName = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    role = serializers.CharField()
    county = serializers.CharField(allow_null=True, allow_blank=True)
    preferredLanguage = serializers.CharField()


class DashboardStatsSerializer(serializers.Serializer):
    coursesStarted = serializers.IntegerField()
    coursesCompleted = serializers.IntegerField()
    badgesEarned = serializers.IntegerField()
    lessonsCompleted = serializers.IntegerField()
    minutesLearned = serializers.IntegerField()
    streak = serializers.IntegerField()


class InProgressCourseSerializer(serializers.Serializer):
    courseId = serializers.CharField()
    slug = serializers.CharField()
    title = serializers.CharField()
    image = serializers.CharField(allow_blank=True)
    alt = serializers.CharField(allow_blank=True)
    subject = serializers.CharField()
    subjectLabel = serializers.CharField()
    level = serializers.CharField()
    hours = serializers.IntegerField()
    done = serializers.IntegerField()
    total = serializers.IntegerField()
    percent = serializers.IntegerField()
    lastLessonId = serializers.CharField(allow_null=True)
    lastLessonSlug = serializers.CharField(allow_null=True, allow_blank=True)
    lastSeenAt = serializers.DateTimeField(allow_null=True)


class RecentBadgeSerializer(serializers.Serializer):
    id = serializers.CharField()
    badgeId = serializers.CharField()
    earnedAt = serializers.DateTimeField()
    courseTitle = serializers.CharField()
    subject = serializers.CharField()
    subjectLabel = serializers.CharField()
    pngUrl = serializers.CharField(allow_null=True, allow_blank=True)


class ActivityDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    percent = serializers.IntegerField()


class RecommendedCourseSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField()
    title = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    image = serializers.CharField(allow_blank=True)
    alt = serializers.CharField(allow_blank=True)
    subject = serializers.CharField()
    subjectLabel = serializers.CharField()
    level = serializers.CharField()
    levelLabel = serializers.CharField()
    rating = serializers.FloatField()
    hours = serializers.IntegerField()
    lessons = serializers.IntegerField()


class FieldDayMiniSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField()
    title = serializers.CharField()
    county = serializers.CharField()
    venue = serializers.CharField()
    startsAt = serializers.DateTimeField()
    endsAt = serializers.DateTimeField()
    topic = serializers.CharField()
    topicLabel = serializers.CharField()
    spots = serializers.IntegerField()
    spotsLeft = serializers.IntegerField()


class LearnerDashboardSerializer(serializers.Serializer):
    """Documentation for the full learner dashboard payload."""
    user = DashboardUserSerializer()
    stats = DashboardStatsSerializer()
    inProgress = InProgressCourseSerializer(many=True)
    completed = InProgressCourseSerializer(many=True)
    recentBadges = RecentBadgeSerializer(many=True)
    weeklyActivity = ActivityDaySerializer(many=True)
    recommended = RecommendedCourseSerializer(many=True)
    fieldDays = FieldDayMiniSerializer(many=True)
    generatedAt = serializers.DateTimeField()