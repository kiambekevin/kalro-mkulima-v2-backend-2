# apps/progress/views.py
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course, Lesson
from apps.courses.selectors import course_by_slug

from .filters import CourseProgressFilter, LessonCompletionFilter
from .models import CourseProgress, LessonCompletion, DailyActivity
from .permissions import IsProgressOwner
from .selectors import (
    activity_last_n_days,
    current_streak,
    is_active_today,
    longest_streak,
    progress_for_course,
    resume_lesson,
)
from .serializers import (
    CourseProgressSerializer,
    DailyActivitySerializer,
    LessonCompletionSerializer,
    StreakSerializer,
    ToggleLessonSerializer,
    UpdateLastLessonSerializer,
)
from .services import complete_lesson, toggle_lesson, uncomplete_lesson, set_last_lesson
from .services import rebuild_course_progress


# ───────────────────────────── Course progress ─────────────────────────────

class MyProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """
    The learner's progress across courses.
      GET    /api/v1/progress/                     → list all progress
      GET    /api/v1/progress/{course_slug}/       → progress for a course
      GET    /api/v1/progress/{course_slug}/resume/→ resume lesson
      POST   /api/v1/progress/{course_slug}/rebuild/→ recompute from scratch
    """
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated, IsProgressOwner]
    filterset_class = CourseProgressFilter
    lookup_field = "course__slug"
    lookup_url_kwarg = "course_slug"

    def get_queryset(self):
        return (
            CourseProgress.objects
            .for_user(self.request.user)
            .with_course()
        )

    def get_object(self):
        course = get_object_or_404(Course, slug=self.kwargs["course_slug"])
        cp = progress_for_course(self.request.user, course)
        if not cp:
            from django.http import Http404
            raise Http404("No progress found for this course.")
        self.check_object_permissions(self.request, cp)
        return cp

    @action(detail=True, methods=["get"])
    def resume(self, request, course_slug=None):
        course = get_object_or_404(Course, slug=course_slug)
        lesson = resume_lesson(request.user, course)
        return Response({"lesson": lesson})

    @action(detail=True, methods=["post"])
    def rebuild(self, request, course_slug=None):
        course = get_object_or_404(Course, slug=course_slug)
        cp = rebuild_course_progress(request.user, course)
        return Response(CourseProgressSerializer(cp).data)


# ───────────────────────────── Lesson completion ─────────────────────────────

class LessonCompletionView(APIView):
    """
    Endpoints for marking a single lesson complete / incomplete.
      POST /api/v1/progress/lessons/{lesson_id}/complete/
      POST /api/v1/progress/lessons/{lesson_id}/uncomplete/
      POST /api/v1/progress/lessons/{lesson_id}/toggle/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id, action):
        lesson = get_object_or_404(Lesson, id=lesson_id)

        if action == "complete":
            cp = complete_lesson(request.user, lesson)
        elif action == "uncomplete":
            cp = uncomplete_lesson(request.user, lesson)
        elif action == "toggle":
            serializer = ToggleLessonSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            cp, _ = toggle_lesson(request.user, lesson, force=serializer.validated_data["force"])
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CourseProgressSerializer(cp).data)


# ───────────────────────────── Last lesson ─────────────────────────────

class SetLastLessonView(APIView):
    """
    POST /api/v1/progress/courses/{slug}/last-lesson/
    Called by the lesson viewer on every lesson load.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        serializer = UpdateLastLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = get_object_or_404(Lesson, id=serializer.validated_data["lesson_id"])
        cp = set_last_lesson(request.user, course, lesson)
        return Response(CourseProgressSerializer(cp).data)


# ───────────────────────────── Activity ─────────────────────────────

class ActivityView(APIView):
    """
    GET /api/v1/progress/activity/?days=7
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        days = max(1, min(days, 90))
        qs = activity_last_n_days(request.user, n=days)
        return Response(DailyActivitySerializer(qs, many=True).data)


class StreakView(APIView):
    """
    GET /api/v1/progress/streak/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = {
            "current": current_streak(request.user),
            "longest": longest_streak(request.user),
            "active_today": is_active_today(request.user),
            "last_active_date": (
                DailyActivity.objects
                .filter(user=request.user, lessons_completed__gte=1)
                .order_by("-date")
                .values_list("date", flat=True)
                .first()
            ),
        }
        return Response(StreakSerializer(payload).data)


class MyLessonCompletionsView(APIView):
    """
    GET /api/v1/progress/completions/?course={slug}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            LessonCompletion.objects
            .for_user(request.user)
            .select_related("lesson", "course")
        )
        course_slug = request.query_params.get("course")
        if course_slug:
            qs = qs.filter(course__slug=course_slug)
        return Response(LessonCompletionSerializer(qs, many=True).data)