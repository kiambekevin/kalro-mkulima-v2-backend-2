# apps/progress/urls.py
"""
Progress URLs that aren't ViewSets.

The `MyProgressViewSet` (list, retrieve, resume, rebuild) is registered
on api/v1/routers.py as `progress`. This file only declares the custom
APIViews.
"""
from django.urls import path

from .views import (
    ActivityView,
    LessonCompletionView,
    MyLessonCompletionsView,
    SetLastLessonView,
    StreakView,
)

app_name = "progress"

urlpatterns = [
    # ── Lesson actions ────────────────────────────────────────
    # POST /api/v1/progress/lessons/{lesson_id}/complete/
    # POST /api/v1/progress/lessons/{lesson_id}/uncomplete/
    # POST /api/v1/progress/lessons/{lesson_id}/toggle/
    path(
        "progress/lessons/<uuid:lesson_id>/<str:action>/",
        LessonCompletionView.as_view(),
        name="lesson-action",
    ),

    # ── Last viewed lesson (used by the Resume button) ───────
    # POST /api/v1/progress/courses/{slug}/last-lesson/
    path(
        "progress/courses/<slug:slug>/last-lesson/",
        SetLastLessonView.as_view(),
        name="last-lesson",
    ),

    # ── Learner aggregates ────────────────────────────────────
    # GET /api/v1/progress/activity/?days=7
    path("progress/activity/", ActivityView.as_view(), name="activity"),

    # GET /api/v1/progress/streak/
    path("progress/streak/", StreakView.as_view(), name="streak"),

    # GET /api/v1/progress/completions/?course={slug}
    path("progress/completions/", MyLessonCompletionsView.as_view(), name="completions"),
]