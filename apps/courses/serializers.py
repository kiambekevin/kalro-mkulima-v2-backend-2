# apps/courses/serializers.py
"""
Course serializers.

Conventions:

1. Every file-backed field (`image`, `resource_file`, resource `url`) is
   emitted as a fully-qualified URL when the serializer has a `request`
   in context. When it doesn't, it emits a `/media/...` path that the
   frontend's `resolveMediaUrl()` helper can finish.

2. Snake_case on the wire, camelCase in the frontend. Page-level
   adapters handle the mapping.

3. Views MUST pass `context={"request": request}` when constructing a
   serializer manually (e.g. in `@action` methods). GenericViewSet
   methods already do this for you.

See `_absolute_media_url` below for the URL-normalisation rules.
"""
from django.conf import settings
from rest_framework import serializers

from .models import (
    Course,
    Lesson,
    Module,
    Pathway,
    PathwayCourse,
    Resource,
    Subject,
)
from .validators import (
    classify_media_url,
    extract_youtube_id,
    is_youtube_url,
)


# ───────────────────────────── URL helper ─────────────────────────────

def _absolute_media_url(value, request=None):
    """
    Normalise a stored media reference into a URL the frontend can load.

    Inputs and outputs:

        "https://cdn.kalro.org/x.jpg"        → unchanged
        "http://…/media/courses/x.jpg"       → unchanged
        "/media/courses/images/x.jpg"        → origin + path
        "media/courses/images/x.jpg"         → origin + /media/ + path
        "courses/images/x.jpg"               → origin + /media/ + path
        None / "" / whitespace               → None

    When `request` is provided, the result is absolute
    (`http://127.0.0.1:8000/media/...`). Otherwise it's a `/media/...`
    path — still usable by the frontend if it runs `resolveMediaUrl()`.
    """
    if not value:
        return None

    value = str(value).strip()
    if not value:
        return None

    # Absolute URLs pass through untouched
    if value.startswith(("http://", "https://")):
        return value

    # Normalise MEDIA_URL to have a leading and trailing slash
    media_url = settings.MEDIA_URL or "/media/"
    if not media_url.startswith("/"):
        media_url = "/" + media_url
    media_url = media_url.rstrip("/") + "/"
    media_prefix = media_url.strip("/")   # e.g. "media"

    # Strip a single leading slash so we can reason about the path
    path = value.lstrip("/")

    # If the value already begins with the media prefix, don't add it again
    if path.startswith(media_prefix + "/"):
        url = "/" + path
    elif path == media_prefix:
        url = media_url
    else:
        url = media_url + path

    return request.build_absolute_uri(url) if request else url


# ───────────────────────────── Subject ─────────────────────────────

class SubjectSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Subject
        fields = ["id", "slug", "label", "icon", "description", "order", "course_count"]
        read_only_fields = ["id"]


# ───────────────────────────── Lesson (outline) ─────────────────────────────

class LessonOutlineSerializer(serializers.ModelSerializer):
    """
    Compact lesson payload for the curriculum accordion. Emits both `id`
    and `slug` so the frontend can build links either way.
    """
    preview = serializers.BooleanField(source="is_preview", read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "slug", "title", "minutes", "type", "order", "preview"]
        read_only_fields = fields


class ModuleOutlineSerializer(serializers.ModelSerializer):
    lessons = LessonOutlineSerializer(many=True, read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ["id", "title", "summary", "order", "duration", "lessons"]
        read_only_fields = fields

    def get_duration(self, obj):
        minutes = sum(l.minutes for l in obj.lessons.all())
        hours = round(minutes / 60, 1)
        return f"{hours} hr{'s' if hours != 1 else ''}"


# ───────────────────────────── Resource ─────────────────────────────

class ResourceSerializer(serializers.ModelSerializer):
    """
    Resource attached to a lesson. Emits an absolute URL for either the
    uploaded file or the external link.
    """
    url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            "id", "kind", "title", "publisher", "description",
            "url", "size_label", "category", "order",
        ]
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        # Prefer the uploaded file
        if obj.file:
            try:
                return _absolute_media_url(obj.file.url, request=request)
            except Exception:
                return None
        return obj.url or None


# ───────────────────────────── Lesson (full) ─────────────────────────────

class LessonSerializer(serializers.ModelSerializer):
    """
    Full lesson payload for the viewer page. Emits everything the
    frontend needs in a single request.
    """
    stream_url = serializers.URLField(allow_blank=True)
    poster_url = serializers.URLField(allow_blank=True, required=False)

    # Derived fields
    youtube_id = serializers.SerializerMethodField()
    stream_media_type = serializers.SerializerMethodField()
    resource_file = serializers.SerializerMethodField()
    resource_media_type = serializers.SerializerMethodField()

    # Nested content
    resources = ResourceSerializer(many=True, read_only=True)
    modules = serializers.SerializerMethodField()

    # Course context
    course_slug = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    module_title = serializers.SerializerMethodField()
    level_label = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id", "slug", "title", "body", "type", "minutes",
            "order", "is_preview",
            "stream_url", "poster_url",
            "youtube_id", "stream_media_type",
            "resource_file", "resource_label", "resource_media_type",
            "notes", "resources", "modules",
            "course_slug", "course_title", "module_title",
            "level_label", "total_lessons",
        ]
        read_only_fields = fields

    # ── Media classification ─────────────────────────────────

    def get_youtube_id(self, obj):
        if obj.stream_url and is_youtube_url(obj.stream_url):
            return extract_youtube_id(obj.stream_url)
        return None

    def get_stream_media_type(self, obj):
        return classify_media_url(obj.stream_url) if obj.stream_url else None

    def get_resource_file(self, obj):
        if not obj.resource_file:
            return None
        request = self.context.get("request")
        try:
            return _absolute_media_url(obj.resource_file.url, request=request)
        except Exception:
            return None

    def get_resource_media_type(self, obj):
        if not obj.resource_file:
            return None
        name = (obj.resource_file.name or "").lower()
        if name.endswith((".mp4", ".webm", ".ogg", ".m4v", ".mov")):
            return "video"
        if name.endswith(".pdf"):
            return "pdf"
        if name.endswith((".mp3", ".wav", ".m4a")):
            return "audio"
        return "file"

    # ── Course context ───────────────────────────────────────

    def get_course_slug(self, obj):
        return obj.module.course.slug

    def get_course_title(self, obj):
        return obj.module.course.title

    def get_module_title(self, obj):
        return obj.module.title

    def get_level_label(self, obj):
        return obj.module.course.get_level_display()

    def get_total_lessons(self, obj):
        return Lesson.objects.filter(module__course=obj.module.course).count()

    # ── Nested curriculum ────────────────────────────────────

    def get_modules(self, obj):
        course = obj.module.course
        modules = (
            course.modules
            .prefetch_related("lessons")
            .order_by("order")
        )
        return ModuleOutlineSerializer(modules, many=True).data


# ───────────────────────────── Course (list) ─────────────────────────────

class CourseListSerializer(serializers.ModelSerializer):
    """
    Payload for the catalogue grid and the popular strip.
    Emits an absolute `image` URL when the serializer has a request.
    """
    subject = serializers.SlugField(source="subject.slug", read_only=True)
    subject_label = serializers.CharField(source="subject.label", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    reviews = serializers.IntegerField(source="review_count", read_only=True)
    lessons = serializers.IntegerField(source="lesson_count", read_only=True)
    badge = serializers.BooleanField(source="badge_enabled", read_only=True)
    image = serializers.SerializerMethodField()
    alt = serializers.CharField(source="alt_text", read_only=True)
    href = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "summary",
            "subject", "subject_label",
            "level", "level_label",
            "rating", "reviews", "hours", "lessons",
            "badge", "popular",
            "image", "alt",
            "updated_source_date",
            "href",
        ]
        read_only_fields = fields

    def get_image(self, obj):
        request = self.context.get("request")
        return _absolute_media_url(obj.image_url, request=request)

    def get_href(self, obj):
        return f"/courses/{obj.slug}"


# ───────────────────────────── Course (detail) ─────────────────────────────

class CourseDetailSerializer(serializers.ModelSerializer):
    subject = serializers.SlugField(source="subject.slug", read_only=True)
    subject_label = serializers.CharField(source="subject.label", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    reviews = serializers.IntegerField(source="review_count", read_only=True)
    lessons = serializers.IntegerField(source="lesson_count", read_only=True)
    badge = serializers.BooleanField(source="badge_enabled", read_only=True)
    image = serializers.SerializerMethodField()
    alt = serializers.CharField(source="alt_text", read_only=True)

    curriculum = serializers.SerializerMethodField()
    instructor = serializers.SerializerMethodField()
    highlights = serializers.SerializerMethodField()
    reviews_sample = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "summary", "description",
            "subject", "subject_label",
            "level", "level_label",
            "rating", "reviews", "hours", "lessons",
            "badge", "popular",
            "image", "alt",
            "updated_source_date",
            "curriculum", "instructor",
            "highlights", "reviews_sample",
        ]
        read_only_fields = fields

    def get_image(self, obj):
        request = self.context.get("request")
        return _absolute_media_url(obj.image_url, request=request)

    def get_curriculum(self, obj):
        modules = (
            obj.modules
            .prefetch_related("lessons")
            .order_by("order")
        )
        return ModuleOutlineSerializer(modules, many=True).data

    def get_instructor(self, obj):
        inst = obj.instructor
        if not inst:
            return None
        return {
            "name": inst.full_name,
            "title": getattr(inst, "job_title", "") or "",
            "initials": inst.initials,
            "colour": "#23804A",
            "bio": getattr(inst, "bio", "") or "",
            "stats": [],
        }

    def get_highlights(self, obj):
        return getattr(obj, "highlights", []) or []

    def get_reviews_sample(self, obj):
        return getattr(obj, "reviews_sample", []) or []


# ───────────────────────────── Pathways ─────────────────────────────

class PathwayCourseItemSerializer(serializers.ModelSerializer):
    """Minimal course payload for a course inside a pathway."""
    course_id = serializers.UUIDField(source="course.id", read_only=True)
    slug = serializers.SlugField(source="course.slug", read_only=True)
    title = serializers.CharField(source="course.title", read_only=True)
    hours = serializers.IntegerField(source="course.hours", read_only=True)
    level_label = serializers.CharField(
        source="course.get_level_display", read_only=True,
    )

    class Meta:
        model = PathwayCourse
        fields = ["course_id", "slug", "title", "hours", "level_label", "order"]
        read_only_fields = fields


class PathwaySerializer(serializers.ModelSerializer):
    """Full pathway payload with the ordered course list."""
    course_count = serializers.IntegerField(read_only=True)
    total_hours = serializers.IntegerField(read_only=True)
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Pathway
        fields = [
            "id", "slug", "title", "summary", "description",
            "icon",
            "badge_label", "badge_variant",
            "cta_variant",
            "course_count", "total_hours",
            "courses",
            "order",
        ]
        read_only_fields = fields

    def get_courses(self, obj):
        links = (
            obj.pathway_courses
            .select_related("course")
            .order_by("order")
        )
        return PathwayCourseItemSerializer(links, many=True).data


class PathwayCompactSerializer(serializers.ModelSerializer):
    """Compact payload for cards / lists."""
    course_count = serializers.IntegerField(read_only=True)
    total_hours = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pathway
        fields = [
            "id", "slug", "title", "summary",
            "icon", "badge_label", "badge_variant", "cta_variant",
            "course_count", "total_hours",
            "order",
        ]
        read_only_fields = fields


# ───────────────────────────── Write serializers ─────────────────────────────

class CourseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "title", "summary", "description",
            "subject", "instructor",
            "level", "hours",
            "badge_enabled", "popular", "is_published",
            "image_url", "alt_text",
            "updated_source_date",
        ]

    def validate_image_url(self, value):
        if not value:
            return value
        # Allow absolute URLs
        if value.startswith(("http://", "https://")):
            return value
        # Allow relative media paths (what the admin submits)
        if "://" in value:
            raise serializers.ValidationError("Only http(s) URLs are allowed.")
        return value


class ModuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["title", "summary", "order"]


class LessonWriteSerializer(serializers.ModelSerializer):
    resources = ResourceSerializer(many=True, required=False)

    class Meta:
        model = Lesson
        fields = [
            "title", "body", "type", "minutes", "order", "is_preview",
            "stream_url", "poster_url", "resource_file", "resource_label",
            "notes", "resources",
        ]

    def create(self, validated_data):
        resources_data = validated_data.pop("resources", [])
        lesson = Lesson.objects.create(**validated_data)
        for r in resources_data:
            Resource.objects.create(lesson=lesson, **r)
        return lesson

    def update(self, instance, validated_data):
        resources_data = validated_data.pop("resources", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if resources_data is not None:
            instance.resources.all().delete()
            for r in resources_data:
                Resource.objects.create(lesson=instance, **r)

        return instance


class PathwayWriteSerializer(serializers.ModelSerializer):
    course_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True,
    )

    class Meta:
        model = Pathway
        fields = [
            "title", "summary", "description", "icon",
            "badge_label", "badge_variant", "cta_variant",
            "is_published", "order",
            "course_ids",
        ]

    def create(self, validated_data):
        course_ids = validated_data.pop("course_ids", [])
        pathway = Pathway.objects.create(**validated_data)
        for i, cid in enumerate(course_ids, start=1):
            PathwayCourse.objects.create(pathway=pathway, course_id=cid, order=i)
        return pathway

    def update(self, instance, validated_data):
        course_ids = validated_data.pop("course_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if course_ids is not None:
            instance.pathway_courses.all().delete()
            for i, cid in enumerate(course_ids, start=1):
                PathwayCourse.objects.create(pathway=instance, course_id=cid, order=i)

        return instance