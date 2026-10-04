# apps/badges/urls.py
"""
Badge URLs that aren't ViewSets.

The `MyBadgesViewSet` and `BadgeTemplateViewSet` are registered on
api/v1/routers.py as `badges` and `badge-templates`. This file only
declares:
  - public verification (`/badges/verify/{id}/`)
  - public PNG download (`/badges/{id}/png/`)
  - admin-only actions (`issue`, `revoke`, `regenerate`)
"""
from django.urls import path

from .views import (
    BadgeIssueView,
    BadgePngView,
    BadgeRegenerateView,
    BadgeRevokeView,
    BadgeVerifyView,
)

app_name = "badges"

urlpatterns = [
    # ── Public: verify ────────────────────────────────────────
    # GET /api/v1/badges/verify/{badge_id}/
    path(
        "badges/verify/<str:badge_id>/",
        BadgeVerifyView.as_view(),
        name="verify",
    ),

    # ── Public: PNG download ──────────────────────────────────
    # GET /api/v1/badges/{badge_id}/png/?variant=plain|with-qr
    path(
        "badges/<str:badge_id>/png/",
        BadgePngView.as_view(),
        name="png",
    ),

    # ── Admin: manual issuance ────────────────────────────────
    # POST /api/v1/badges/issue/
    path("badges/issue/", BadgeIssueView.as_view(), name="issue"),

    # ── Admin: revoke ─────────────────────────────────────────
    # POST /api/v1/badges/{badge_id}/revoke/
    path(
        "badges/<str:badge_id>/revoke/",
        BadgeRevokeView.as_view(),
        name="revoke",
    ),

    # ── Admin: regenerate PNG ─────────────────────────────────
    # POST /api/v1/badges/{badge_id}/regenerate/
    path(
        "badges/<str:badge_id>/regenerate/",
        BadgeRegenerateView.as_view(),
        name="regenerate",
    ),
]