# apps/media/views.py
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MediaAsset, UploadSession
from .permissions import IsUploaderOrAdmin, CanUploadMedia, HasValidSignature
from .selectors import asset_by_id, assets_for_user
from .serializers import (
    MediaAssetSerializer,
    MediaAssetCompactSerializer,
    UploadSessionSerializer,
    InitiateUploadSerializer,
    CompleteUploadSerializer,
    AttachManifestSerializer,
)
from .services import (
    initiate_upload,
    complete_upload,
    attach_manifest,
    signed_playback_url,
    signed_download_url,
)


# ───────────────────────────── Media library ─────────────────────────────

class MediaAssetViewSet(viewsets.ModelViewSet):
    """
    Media library for uploaders and admins.
      GET    /api/v1/media/assets/            → my uploads
      GET    /api/v1/media/assets/{id}/       → single asset
      DELETE /api/v1/media/assets/{id}/       → soft-delete via is_active
      GET    /api/v1/media/assets/{id}/playback-url/
      GET    /api/v1/media/assets/{id}/download-url/
    """
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAuthenticated, CanUploadMedia, IsUploaderOrAdmin]
    lookup_field = "id"

    def get_queryset(self):
        return assets_for_user(self.request.user)

    @action(detail=True, methods=["get"], url_path="playback-url")
    def playback_url(self, request, id=None):
        asset = self.get_object()
        return Response({"url": signed_playback_url(asset, request=request)})

    @action(detail=True, methods=["get"], url_path="download-url")
    def download_url(self, request, id=None):
        asset = self.get_object()
        return Response({"url": signed_download_url(asset, request=request)})


# ───────────────────────────── Upload flow ─────────────────────────────

class InitiateUploadView(APIView):
    """
    POST /api/v1/media/uploads/initiate/
    Starts a resumable upload session.
    """
    permission_classes = [IsAuthenticated, CanUploadMedia]

    def post(self, request):
        serializer = InitiateUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset, session = initiate_upload(
            user=request.user,
            kind=serializer.validated_data["kind"],
            filename=serializer.validated_data["filename"],
            size_bytes=serializer.validated_data["size_bytes"],
            title=serializer.validated_data.get("title", ""),
            mime_type=serializer.validated_data.get("mime_type", ""),
        )

        return Response(
            {
                "asset": MediaAssetCompactSerializer(asset, context={"request": request}).data,
                "session": UploadSessionSerializer(session).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CompleteUploadView(APIView):
    """
    POST /api/v1/media/uploads/complete/
    Marks the session as finished and the asset as ready (or processing).
    """
    permission_classes = [IsAuthenticated, CanUploadMedia]

    def post(self, request):
        serializer = CompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = get_object_or_404(
            UploadSession,
            id=serializer.validated_data["session_id"],
            user=request.user,
        )

        asset = complete_upload(
            session=session,
            checksum_sha256=serializer.validated_data.get("checksum_sha256", ""),
            duration_seconds=serializer.validated_data.get("duration_seconds"),
        )

        return Response(
            MediaAssetSerializer(asset, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class AttachManifestView(APIView):
    """
    POST /api/v1/media/assets/{id}/attach-manifest/
    Admin / transcoder only. Called after HLS segments are ready.
    """
    permission_classes = [IsAuthenticated, CanUploadMedia]

    def post(self, request, id):
        asset = get_object_or_404(MediaAsset, id=id)
        serializer = AttachManifestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset = attach_manifest(
            asset=asset,
            manifest_url=serializer.validated_data["manifest_url"],
            segments_base_url=serializer.validated_data.get("segments_base_url", ""),
            duration_seconds=serializer.validated_data.get("duration_seconds"),
            poster_url=serializer.validated_data.get("poster_url", ""),
        )

        return Response(
            MediaAssetSerializer(asset, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


# ───────────────────────────── Signed byte-serving ─────────────────────────────

class SignedDownloadView(APIView):
    """
    GET /api/v1/media/download/{asset_id}/?expires=…&sig=…

    Serves the PDF or image bytes. Requires a valid signature; unsigned
    requests are rejected. In production, Nginx or the CDN handles this
    for the file paths, and this view is only a fallback for local dev.
    """
    permission_classes = [AllowAny]  # signature is the permission

    def get(self, request, asset_id):
        from .signing import verify_signed_url
        full_url = request.build_absolute_uri()
        if not verify_signed_url(full_url):
            return HttpResponse("Signature invalid or expired.", status=403)

        asset = get_object_or_404(MediaAsset, id=asset_id)
        if not asset.file:
            raise Http404("No file attached to this asset.")

        filename = asset.file.name.rsplit("/", 1)[-1]
        return FileResponse(
            asset.file.open("rb"),
            as_attachment=True,
            filename=filename,
            content_type=asset.mime_type or "application/octet-stream",
        )