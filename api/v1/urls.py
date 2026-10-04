# api/v1/urls.py
"""
Aggregate URL configuration for /api/v1/.

Each app exposes two kinds of URL:
  1. Custom APIViews declared in `apps/<app>/urls.py` — included here
     with an explicit namespace.
  2. ViewSets registered on the shared router in `api/v1/routers.py` —
     unpacked at the bottom.

Do NOT include `apps.courses.urls` before the router if course
ViewSets are also on the router — that would create duplicate routes.
"""
from django.urls import include, path

from . import router as api_routers


urlpatterns = [
    # ── Auth: register, login, logout, me, availability checks ──
    path("auth/", include("apps.accounts.urls", namespace="accounts")),

    # ── Badges: public verify, PNG download, admin issue/revoke ──
    path("", include("apps.badges.urls", namespace="badges")),

    # ── Field days: check-in, attendance ──
    path("", include("apps.fielddays.urls", namespace="fielddays")),

    # ── Dashboard: learner + county ──
    path("", include("apps.dashboard.urls", namespace="dashboard")),

    # ── Media: signed URLs, upload sessions ──
    path("", include("apps.media.urls", namespace="media_library")),

    # ── Courses: lesson viewer + admin authoring (nested paths only) ──
    path("", include("apps.courses.urls", namespace="courses")),

    path("", include("apps.analytics.urls", namespace="analytics")),

    # ── Router-registered ViewSets (subjects, courses, progress, counties, …) ──
    *api_routers.urlpatterns,
]