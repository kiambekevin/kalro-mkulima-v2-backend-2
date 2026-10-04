# apps/media/urls.py
"""
Media library URLs that aren't ViewSets.

The `MediaAssetViewSet` (list, detail, delete, playback-url,
download-url) is registered on api/v1/routers.py as `media/assets`.
This file declares:
  - upload session lifecycle (initiate, complete)
  - manifest attachment (transcoder callback)
  - signed byte-serving (dev fallback for direct downloads)
"""
from django.urls import path

from .views import (
    AttachManifestView,
    CompleteUploadView,
    InitiateUploadView,
    SignedDownloadView,
)

app_name = "media_library"

urlpatterns = [
    # ── Upload lifecycle ──────────────────────────────────────
    # POST /api/v1/media/uploads/initiate/
    path(
        "media/uploads/initiate/",
        InitiateUploadView.as_view(),
        name="upload-initiate",
    ),

    # POST /api/v1/media/uploads/complete/
    path(
        "media/uploads/complete/",
        CompleteUploadView.as_view(),
        name="upload-complete",
    ),

    # ── Manifest attachment ───────────────────────────────────
    # POST /api/v1/media/assets/{id}/attach-manifest/
    # (used by the transcoder webhook; admin can trigger manually)
    path(
        "media/assets/<uuid:id>/attach-manifest/",
        AttachManifestView.as_view(),
        name="attach-manifest",
    ),

    # ── Signed byte-serving (dev fallback) ────────────────────
    # GET /api/v1/media/download/{asset_id}/?expires=&sig=
    path(
        "media/download/<uuid:asset_id>/",
        SignedDownloadView.as_view(),
        name="download",
    ),
]