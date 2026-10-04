# apps/media/serializers.py
from rest_framework import serializers

from .models import MediaAsset, UploadSession


class MediaAssetSerializer(serializers.ModelSerializer):
    """
    Read serializer for media assets.

    The `playback_url` and `download_url` fields are short-lived signed
    URLs. They are computed per request — never stored.
    """
    playback_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    kind = serializers.CharField()
    status = serializers.CharField()

    class Meta:
        model = MediaAsset
        fields = [
            "id", "slug", "kind", "status", "title",
            "manifest_url", "segments_base_url", "poster_url",
            "mime_type", "size_bytes",
            "duration_seconds", "width", "height",
            "playback_url", "download_url",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_playback_url(self, obj):
        """Signed URL for HLS/DASH playback."""
        if obj.kind != MediaAsset.Kind.VIDEO or not obj.manifest_url:
            return ""
        from .services import signed_playback_url
        return signed_playback_url(obj, request=self.context.get("request"))

    def get_download_url(self, obj):
        """Signed URL for PDF/image download."""
        if obj.kind not in (MediaAsset.Kind.PDF, MediaAsset.Kind.IMAGE):
            return ""
        if not obj.file:
            return ""
        from .services import signed_download_url
        return signed_download_url(obj, request=self.context.get("request"))


class MediaAssetCompactSerializer(serializers.ModelSerializer):
    """Small payload for embedding in lesson/resource payloads."""
    playback_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    kind = serializers.CharField()
    status = serializers.CharField()

    class Meta:
        model = MediaAsset
        fields = [
            "id", "slug", "kind", "status", "title",
            "poster_url", "duration_seconds",
            "playback_url", "download_url",
        ]

    def get_playback_url(self, obj):
        if obj.kind != MediaAsset.Kind.VIDEO or not obj.manifest_url:
            return ""
        from .services import signed_playback_url
        return signed_playback_url(obj, request=self.context.get("request"))

    def get_download_url(self, obj):
        if obj.kind != MediaAsset.Kind.PDF or not obj.file:
            return ""
        from .services import signed_download_url
        return signed_download_url(obj, request=self.context.get("request"))


class UploadSessionSerializer(serializers.ModelSerializer):
    asset = MediaAssetSerializer(read_only=True)
    percent = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = UploadSession
        fields = [
            "id", "asset", "expected_size", "received_bytes",
            "upload_url", "upload_fields",
            "percent", "is_expired",
            "completed_at", "expires_at", "created_at",
        ]
        read_only_fields = fields


class InitiateUploadSerializer(serializers.Serializer):
    """
    Payload for starting an upload.

      kind         — 'video' | 'pdf' | 'image'
      title        — optional human-readable label
      filename     — original filename (used to derive the slug)
      size_bytes   — expected final size
      mime_type    — optional, verified against kind
    """
    kind = serializers.ChoiceField(choices=MediaAsset.Kind.choices)
    title = serializers.CharField(required=False, allow_blank=True, max_length=180)
    filename = serializers.CharField(max_length=255)
    size_bytes = serializers.IntegerField(min_value=1)
    mime_type = serializers.CharField(required=False, allow_blank=True, max_length=80)


class CompleteUploadSerializer(serializers.Serializer):
    """
    Payload for closing an upload session after the client has pushed
    all bytes to S3 (or posted the file to Django).

      session_id        — the upload session
      checksum_sha256   — optional integrity check
      duration_seconds  — for videos, measured client-side
    """
    session_id = serializers.UUIDField()
    checksum_sha256 = serializers.CharField(required=False, allow_blank=True, max_length=64)
    duration_seconds = serializers.IntegerField(required=False, min_value=0)


class AttachManifestSerializer(serializers.Serializer):
    """
    Attach a pre-transcoded HLS/DASH manifest to a video asset.

      manifest_url       — master .m3u8 or .mpd
      segments_base_url  — optional prefix for segments
      duration_seconds   — optional runtime
      poster_url         — optional poster frame
    """
    manifest_url = serializers.URLField()
    segments_base_url = serializers.URLField(required=False, allow_blank=True)
    duration_seconds = serializers.IntegerField(required=False, min_value=0)
    poster_url = serializers.URLField(required=False, allow_blank=True)