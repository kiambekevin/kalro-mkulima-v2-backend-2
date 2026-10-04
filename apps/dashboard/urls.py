# apps/dashboard/urls.py
"""
Dashboard URLs.

The dashboard is composed entirely of custom APIViews — no ViewSets,
because the payloads are aggregated blobs, not REST resources.
"""
from django.urls import path

from .views import (
    CountyDashboardView,
    DashboardRefreshView,
    LearnerDashboardView,
)

app_name = "dashboard"

urlpatterns = [
    # ── Learner dashboard ─────────────────────────────────────
    # GET /api/v1/dashboard/             → full payload
    # GET /api/v1/dashboard/?refresh=true → bypass cache
    path("dashboard/", LearnerDashboardView.as_view(), name="learner"),

    # ── Manual cache clear ────────────────────────────────────
    # POST /api/v1/dashboard/refresh/
    path("dashboard/refresh/", DashboardRefreshView.as_view(), name="refresh"),

    # ── County dashboard ──────────────────────────────────────
    # GET /api/v1/dashboard/county/{code}/
    path(
        "dashboard/county/<str:code>/",
        CountyDashboardView.as_view(),
        name="county",
    ),
]