# apps/badges/serializers.py
from rest_framework import serializers

from .models import Badge, BadgeTemplate, BadgeVerification
from .qr import verification_url


# ───────────────────────────── Template ─────────────────────────────

class BadgeTemplateSerializer(serializers.ModelSerializer):
    subject_label = serializers.CharField(source="subject.label", read_only=True)

    class Meta:
        model = BadgeTemplate
        fields = [
            "id", "subject", "subject_label",
            "tint_hex", "accent_hex", "icon", "label",
        ]
        read_only_fields = ["id"]


# ───────────────────────────── Badge ─────────────────────────────

class BadgeSerializer(serializers.ModelSerializer):
    """
    Full badge representation used by the wallet page and detail views.
    Includes the snapshot, PNG URL, and public verify URL.
    """
    subject = serializers.SerializerMethodField()
    subject_label = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    hours = serializers.SerializerMethodField()
    earned_at = serializers.DateTimeField(source="issued_at", read_only=True)
    png_url = serializers.SerializerMethodField()
    verify_url = serializers.SerializerMethodField()
    is_verifiable = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Badge
        fields = [
            "id", "badge_id",
            "subject", "subject_label",
            "course_title", "level", "hours",
            "earned_at",
            "status", "is_verifiable", "is_expired",
            "expires_at", "revoked_at",
            "png_url", "verify_url",
            "snapshot",
        ]
        read_only_fields = fields

    def get_subject(self, obj):
        return obj.snapshot.get("subject") or obj.course.subject.slug

    def get_subject_label(self, obj):
        return obj.snapshot.get("subject_label") or obj.course.subject.label

    def get_course_title(self, obj):
        return obj.snapshot.get("course_title") or obj.course.title

    def get_level(self, obj):
        return obj.snapshot.get("level") or obj.course.level

    def get_hours(self, obj):
        return obj.snapshot.get("hours") or obj.course.hours

    def get_png_url(self, obj):
        if not obj.png_file:
            return None
        request = self.context.get("request")
        url = obj.png_file.url
        return request.build_absolute_uri(url) if request else url

    def get_verify_url(self, obj):
        return verification_url(obj.badge_id)


class BadgeCompactSerializer(serializers.ModelSerializer):
    """Small payload used in lists (dashboard, related badges)."""
    subject = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    earned_at = serializers.DateTimeField(source="issued_at", read_only=True)
    verify_url = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ["id", "badge_id", "subject", "course_title", "earned_at", "verify_url"]
        read_only_fields = fields

    def get_subject(self, obj):
        return obj.snapshot.get("subject") or obj.course.subject.slug

    def get_course_title(self, obj):
        return obj.snapshot.get("course_title") or obj.course.title

    def get_verify_url(self, obj):
        return verification_url(obj.badge_id)


# ───────────────────────────── Verification ─────────────────────────────

class BadgeVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadgeVerification
        fields = ["id", "verified_at", "verifier_ip", "verifier_user_agent"]
        read_only_fields = fields


class PublicVerificationSerializer(serializers.Serializer):
    """
    Response schema for the public verify endpoint. `verified` is False
    for not_found / revoked / expired, and `badge` is null in that case.
    """
    verified = serializers.BooleanField()
    reason = serializers.ChoiceField(
        choices=["ok", "not_found", "revoked", "expired"]
    )
    badge = BadgeSerializer(allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True)


class BadgeIssueSerializer(serializers.Serializer):
    """
    For admins who want to force-issue a badge via API.
    Normal flow is automatic on course completion.
    """
    user_id = serializers.UUIDField()
    course_id = serializers.UUIDField()
    force = serializers.BooleanField(default=False)