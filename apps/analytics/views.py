from django.shortcuts import render

# Create your views here.
# apps/analytics/views.py
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VisitEvent
from .serializers import VisitEventSerializer
from .services import record_course_visit, record_lesson_visit


class TrackVisitView(APIView):
    """
    POST /api/v1/analytics/track/
    Records a course or lesson page view. Public — anonymous visits
    are tracked under a hashed session id.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VisitEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user if request.user.is_authenticated else None
        session_id = request.data.get("session_id", "")
        rt = data["resource_type"]

        if rt == VisitEvent.ResourceType.COURSE:
            event = record_course_visit(
                user=user,
                session_id=session_id,
                course_slug=data["course_slug"],
                request=request,
            )
        else:
            event = record_lesson_visit(
                user=user,
                session_id=session_id,
                course_slug=data["course_slug"],
                lesson_identifier=data["lesson_identifier"],
                request=request,
            )

        if not event:
            return Response(
                {"detail": "Resource not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class VisitStatsView(APIView):
    """
    GET /api/v1/analytics/visits/
    Aggregated visit counts for the admin / county dashboards.

    Query params:
      group_by    course | lesson | county | day   (default: course)
      days        window size in days (default: 30)
      county      filter by county code
      course      filter by course slug
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group_by = request.query_params.get("group_by", "course")
        days = int(request.query_params.get("days", 30))
        county_code = request.query_params.get("county")
        course_slug = request.query_params.get("course")

        qs = VisitEvent.objects.all()
        if county_code:
            qs = qs.filter(county__code=county_code)
        if course_slug:
            qs = qs.filter(course__slug=course_slug)

        from django.utils import timezone
        from datetime import timedelta
        since = timezone.now() - timedelta(days=days)
        qs = qs.filter(created_at__gte=since)

        if group_by == "course":
            rows = (
                qs.filter(resource_type="course")
                .values("course__slug", "course__title")
                .annotate(count=Count("id"))
                .order_by("-count")[:50]
            )
            return Response([
                {"slug": r["course__slug"], "title": r["course__title"], "count": r["count"]}
                for r in rows
            ])

        if group_by == "lesson":
            rows = (
                qs.filter(resource_type="lesson")
                .values(
                    "lesson__slug",
                    "lesson__title",
                    "course__slug",
                    "course__title",
                )
                .annotate(count=Count("id"))
                .order_by("-count")[:100]
            )
            return Response([
                {
                    "lesson_slug": r["lesson__slug"],
                    "lesson_title": r["lesson__title"],
                    "course_slug": r["course__slug"],
                    "course_title": r["course__title"],
                    "count": r["count"],
                }
                for r in rows
            ])

        if group_by == "county":
            rows = (
                qs.exclude(county__isnull=True)
                .values("county__code", "county__name")
                .annotate(count=Count("id"))
                .order_by("-count")
            )
            return Response([
                {"code": r["county__code"], "name": r["county__name"], "count": r["count"]}
                for r in rows
            ])

        if group_by == "day":
            from django.db.models.functions import TruncDate
            rows = (
                qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            )
            return Response([
                {"date": r["day"].isoformat(), "count": r["count"]}
                for r in rows
            ])

        return Response(
            {"detail": "Unknown group_by value."},
            status=status.HTTP_400_BAD_REQUEST,
        )