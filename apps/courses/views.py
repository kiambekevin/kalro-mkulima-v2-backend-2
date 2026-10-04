# apps/courses/views.py
"""
Course, curriculum, and pathway endpoints.

Serializer-construction rules:

1. GenericViewSet methods (`list`, `retrieve`, `create`, `update`)
   already pass the request through `get_serializer_context()` — DRF
   handles this for you.

2. Any hand-constructed serializer call inside an `@action` method
   MUST include `context={"request": request}`. Without it,
   `_absolute_media_url` cannot build an absolute URL, and the frontend
   receives a `/media/...` path that resolves against the wrong origin.

3. Never cache the *serialized output* of an action that emits
   absolute URLs. The host header baked into the cached payload belongs
   to whichever request triggered the first miss. Cache raw querysets
   or IDs; serialize per request.
"""
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import CATALOGUE_CACHE_TTL
from .filters import CourseFilter
from .models import Course, Lesson, Module, Pathway, Resource, Subject
from .permissions import IsAuthorOrAdmin, IsCourseAuthor
from .selectors import (
    course_by_slug,
    course_resources,
    lesson_by_identifier,
    popular_courses,
    published_pathways,
    related_courses,
    subjects_with_counts,
)
from .serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    CourseWriteSerializer,
    LessonSerializer,
    LessonWriteSerializer,
    ModuleOutlineSerializer,
    ModuleWriteSerializer,
    PathwayCompactSerializer,
    PathwaySerializer,
    ResourceSerializer,
    SubjectSerializer,
)


# ───────────────────────────── Subjects ─────────────────────────────

class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of course subjects.

      GET /api/v1/subjects/         → list with course counts
      GET /api/v1/subjects/{slug}/  → single subject
    """
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return subjects_with_counts()


# ───────────────────────────── Pathways ─────────────────────────────

class PathwayViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Pathways of related courses.

      GET /api/v1/pathways/           → list
      GET /api/v1/pathways/{slug}/    → detail with ordered courses
    """
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return published_pathways()

    def get_serializer_class(self):
        return (
            PathwaySerializer
            if self.action == "retrieve"
            else PathwayCompactSerializer
        )


# ───────────────────────────── Courses ─────────────────────────────

class CourseViewSet(viewsets.ModelViewSet):
    """
    Catalogue + detail + curriculum + related + publishing.

      GET    /api/v1/courses/                       → filterable list
      GET    /api/v1/courses/{slug}/                → detail with curriculum
      GET    /api/v1/courses/{slug}/curriculum/     → modules & lessons
      GET    /api/v1/courses/{slug}/resources/      → all lesson resources
      GET    /api/v1/courses/{slug}/related/        → related courses
      GET    /api/v1/courses/popular/               → homepage strip
      POST   /api/v1/courses/{slug}/publish/        → admin publish
      POST   /api/v1/courses/                       → admin create
      PATCH  /api/v1/courses/{slug}/                → admin update
    """
    lookup_field = "slug"
    filterset_class = CourseFilter
    search_fields = ["title", "summary", "description", "subject__label"]
    ordering_fields = ["popular", "rating", "hours", "updated_source_date", "title"]

    def get_queryset(self):
        """
        Base queryset for list/retrieve/update. `list` uses this plus
        the filter backends; `retrieve` overrides via `get_object`
        below to prefetch the full curriculum.
        """
        return (
            Course.objects
            .published()
            .with_instructor()
            .prefetch_related("modules__lessons")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CourseWriteSerializer
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer

    def get_permissions(self):
        if self.action in (
            "create", "update", "partial_update", "destroy", "publish",
        ):
            return [IsCourseAuthor(), IsAuthorOrAdmin()]
        return [AllowAny()]

    def get_object(self):
        """
        Retrieve is loaded via the selector so the full curriculum is
        prefetched in three queries. All other actions use the standard
        `get_queryset` path.
        """
        slug = self.kwargs.get("slug")
        if self.action == "retrieve":
            course = course_by_slug(slug)
        else:
            course = self.get_queryset().filter(slug=slug).first()

        if not course:
            raise Http404

        self.check_object_permissions(self.request, course)
        return course

    # ── Custom actions ──────────────────────────────────────────

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def popular(self, request):
        """
        Homepage strip. Returns the top 6 courses by rating among those
        flagged `popular=True`.

        The serializer MUST receive `context={"request": request}` so
        `image` comes back as an absolute URL. We deliberately do not
        cache the serialized response — the host in the URL depends on
        the incoming request, and caching it would leak `localhost:…`
        to production clients.
        """
        courses = popular_courses(6)
        data = CourseListSerializer(
            courses,
            many=True,
            context={"request": request},
        ).data
        return Response(data)

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def curriculum(self, request, slug=None):
        """
        Modules and lessons in display order. Used by the curriculum tab
        on the course detail page.
        """
        course = self.get_object()
        modules = (
            course.modules
            .prefetch_related("lessons")
            .order_by("order")
        )
        return Response(
            ModuleOutlineSerializer(
                modules,
                many=True,
                context={"request": request},
            ).data
        )

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def resources(self, request, slug=None):
        """
        Every resource attached to any lesson in this course, ordered by
        module → lesson → resource. Used by the resource summary view.
        """
        course = self.get_object()
        resources = course_resources(course)
        return Response(
            ResourceSerializer(
                resources,
                many=True,
                context={"request": request},
            ).data
        )

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def related(self, request, slug=None):
        """
        Related courses for the bottom of the detail page. Prefers
        same-subject courses; falls back to popular ones.
        """
        course = self.get_object()
        related = related_courses(course, limit=4)
        return Response(
            CourseListSerializer(
                related,
                many=True,
                context={"request": request},
            ).data
        )

    @action(detail=True, methods=["post"], permission_classes=[IsCourseAuthor])
    def publish(self, request, slug=None):
        """Admin-only: flip `is_published` after validating the course."""
        from .services import PublishError, publish_course

        course = self.get_object()
        try:
            publish_course(course)
        except PublishError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CourseDetailSerializer(
                course,
                context={"request": request},
            ).data
        )


# ───────────────────────────── Lessons ─────────────────────────────

class LessonView(APIView):
    """
    GET /api/v1/courses/{course_slug}/lessons/{lesson_identifier}/

    `lesson_identifier` accepts either the lesson's slug or its UUID.
    Both forms resolve through `lesson_by_identifier`, so URLs from any
    generation of the frontend work.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_slug, lesson_identifier):
        lesson = lesson_by_identifier(course_slug, lesson_identifier)
        if not lesson:
            return Response(
                {"detail": "Lesson not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            LessonSerializer(lesson, context={"request": request}).data
        )


# ───────────────────────────── Admin authoring ─────────────────────────────

class ModuleViewSet(viewsets.ModelViewSet):
    """
    Admin-only module authoring, nested under a course.

      GET    /api/v1/courses/{course_slug}/modules/
      POST   /api/v1/courses/{course_slug}/modules/
      GET    /api/v1/courses/{course_slug}/modules/{id}/
      PATCH  /api/v1/courses/{course_slug}/modules/{id}/
      DELETE /api/v1/courses/{course_slug}/modules/{id}/
    """
    serializer_class = ModuleWriteSerializer
    permission_classes = [IsCourseAuthor]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Module.objects
            .filter(course__slug=self.kwargs["course_slug"])
            .prefetch_related("lessons")
            .order_by("order")
        )

    def perform_create(self, serializer):
        course = get_object_or_404(Course, slug=self.kwargs["course_slug"])
        serializer.save(course=course)


class LessonAdminViewSet(viewsets.ModelViewSet):
    """
    Admin-only lesson authoring, nested under a module.

      GET    /api/v1/modules/{module_id}/lessons/
      POST   /api/v1/modules/{module_id}/lessons/
      GET    /api/v1/modules/{module_id}/lessons/{id}/
      PATCH  /api/v1/modules/{module_id}/lessons/{id}/
      DELETE /api/v1/modules/{module_id}/lessons/{id}/
    """
    serializer_class = LessonWriteSerializer
    permission_classes = [IsCourseAuthor]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Lesson.objects
            .filter(module_id=self.kwargs["module_id"])
            .select_related("module")
            .prefetch_related("resources")
            .order_by("order")
        )

    def perform_create(self, serializer):
        module = get_object_or_404(Module, id=self.kwargs["module_id"])
        serializer.save(module=module)