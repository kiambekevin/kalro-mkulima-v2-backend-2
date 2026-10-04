# apps/fielddays/serializers.py
from rest_framework import serializers

from .models import FieldDay, Booking, Attendance
from .constants import BOOKING_STATUS_CONFIRMED


# ───────────────────────────── Field day ─────────────────────────────

class FieldDaySerializer(serializers.ModelSerializer):
    """
    Full representation for the detail page and dashboard cards.
    """
    county = serializers.CharField(source="county.name", read_only=True)
    county_code = serializers.CharField(source="county.code", read_only=True)
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)
    topic_label = serializers.CharField(source="topic.label", read_only=True)
    booked = serializers.IntegerField(source="booked_count", read_only=True)
    attended = serializers.IntegerField(source="attended_count", read_only=True)
    waitlisted = serializers.IntegerField(source="waitlisted_count", read_only=True)
    spots_left = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    host_name = serializers.CharField(source="host", read_only=True)

    class Meta:
        model = FieldDay
        fields = [
            "id", "slug", "title", "description",
            "topic", "topic_slug", "topic_label",
            "county", "county_code", "venue", "latitude", "longitude",
            "starts_at", "ends_at", "timezone_name",
            "spots", "spots_left", "is_full",
            "booked", "attended", "waitlisted",
            "host_name", "contact_phone", "contact_email",
            "status",
            "is_upcoming", "is_past",
            "cover_image_url", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class FieldDayCompactSerializer(serializers.ModelSerializer):
    """
    Small payload for the dashboard 'Upcoming field days' panel.
    """
    county = serializers.CharField(source="county.name", read_only=True)
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)
    topic_label = serializers.CharField(source="topic.label", read_only=True)
    spots_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = FieldDay
        fields = [
            "id", "slug", "title",
            "topic_slug", "topic_label",
            "county", "venue",
            "starts_at", "ends_at",
            "spots", "spots_left",
            "host",
            "status",
        ]


class FieldDayWriteSerializer(serializers.ModelSerializer):
    """Create/update payload for county officers and admins."""

    class Meta:
        model = FieldDay
        fields = [
            "title", "description",
            "topic", "county", "venue",
            "latitude", "longitude",
            "starts_at", "ends_at", "timezone_name",
            "spots", "waitlist_enabled",
            "host", "host_user",
            "contact_phone", "contact_email",
            "status", "cover_image_url", "notes",
        ]

    def validate(self, data):
        from .validators import validate_end_after_start
        start = data.get("starts_at")
        end = data.get("ends_at")
        validate_end_after_start(start, end)
        return data


# ───────────────────────────── Booking ─────────────────────────────

class BookingSerializer(serializers.ModelSerializer):
    field_day = FieldDayCompactSerializer(read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    can_check_in = serializers.BooleanField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "code", "status", "status_label",
            "field_day", "user_email", "user_name",
            "booked_at", "cancelled_at",
            "can_check_in",
        ]
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    """
    Payload for POST /fielddays/{slug}/book/
    Only `field_day` comes from the URL; everything else is server-derived.
    """
    field_day_slug = serializers.CharField(required=False, allow_blank=True)


# ───────────────────────────── Attendance ─────────────────────────────

class AttendanceSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="booking.user.email", read_only=True)
    user_name = serializers.CharField(source="booking.user.full_name", read_only=True)
    booking_code = serializers.CharField(source="booking.code", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id", "booking", "booking_code",
            "user_email", "user_name",
            "checked_in_at", "checked_in_by",
            "latitude", "longitude", "notes",
        ]
        read_only_fields = fields


class CheckinSerializer(serializers.Serializer):
    """
    Payload for POST /fielddays/checkin/
    Either `code` (the booking's short code) or `booking_id` is required.
    """
    code = serializers.CharField(required=False, allow_blank=True, max_length=12)
    booking_id = serializers.UUIDField(required=False)
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get("code") and not data.get("booking_id"):
            raise serializers.ValidationError(
                "Provide either a booking code or a booking ID."
            )
        return data