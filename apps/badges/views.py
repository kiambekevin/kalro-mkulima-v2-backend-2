# apps/badges/views.py
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Badge, BadgeTemplate
from .permissions import IsBadgeOwnerOrAdmin, IsAdminOrTemplateEditor
from .selectors import (
    badges_for_user,
    badge_by_public_id,
    verifications_for_badge,
)
from .serializers import (
    BadgeSerializer,
    BadgeCompactSerializer,
    BadgeTemplateSerializer,
    BadgeVerificationSerializer,
    PublicVerificationSerializer,
    BadgeIssueSerializer,
)
from .services import verify_badge, issue_badge
from .renderers import render_badge_png_bytes, render_badge_with_qr_png_bytes
from . import tasks


# ───────────────────────────── Wallet (my badges) ─────────────────────────────

class MyBadgesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Authenticated learner's wallet.
      GET /api/v1/badges/                → list
      GET /api/v1/badges/{badge_id}/     → detail (badge_id, not UUID)
      GET /api/v1/badges/{badge_id}/png/ → binary PNG
    """
    permission_classes = [IsAuthenticated, IsBadgeOwnerOrAdmin]
    lookup_field = "badge_id"
    lookup_url_kwarg = "badge_id"

    def get_queryset(self):
        return badges_for_user(self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return BadgeSerializer
        return BadgeSerializer

    @action(detail=True, methods=["get"], url_path="png")
    def png(self, request, badge_id=None):
        badge = self.get_object()
        png_bytes = render_badge_png_bytes(badge)
        return Response(
            {"detail": "Use the /png-with-qr/ endpoint or the storage URL."},
        )

    @action(detail=True, methods=["get"], url_path="verifications")
    def verifications(self, request, badge_id=None):
        badge = self.get_object()
        qs = verifications_for_badge(badge)
        return Response(BadgeVerificationSerializer(qs, many=True).data)


# ───────────────────────────── Badge templates ─────────────────────────────

class BadgeTemplateViewSet(viewsets.ModelViewSet):
    """
    Admin-managed colour + icon per subject.
      GET /api/v1/badge-templates/      → public read
      PATCH /api/v1/badge-templates/{id}/ → admin only
    """
    queryset = BadgeTemplate.objects.select_related("subject").all()
    serializer_class = BadgeTemplateSerializer
    permission_classes = [IsAdminOrTemplateEditor]


# ───────────────────────────── Public verification ─────────────────────────────

class BadgeVerifyView(APIView):
    """
    Public verification endpoint. No auth required — the whole point is
    that anyone (buyer, cooperative, county officer) can check a badge.

      GET /api/v1/badges/verify/{badge_id}/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, badge_id):
        badge, reason = verify_badge(badge_id, request=request)
        serializer = PublicVerificationSerializer({
            "verified": reason == "ok",
            "reason": reason,
            "badge": BadgeSerializer(badge, context={"request": request}).data if badge else None,
            "message": _reason_message(reason, badge),
        })
        http_status = (
            status.HTTP_200_OK if reason in ("ok", "revoked", "expired")
            else status.HTTP_404_NOT_FOUND
        )
        return Response(serializer.data, status=http_status)


def _reason_message(reason: str, badge: Badge | None) -> str:
    if reason == "ok":
        return "This badge was issued by KALRO Mkulima and matches the registry record."
    if reason == "revoked":
        return "This badge has been revoked and is no longer valid."
    if reason == "expired":
        return "This badge has expired. Contact KALRO for a re-issue."
    return "No badge found with this ID. Check the characters under the QR code."


# ───────────────────────────── PNG download (public) ─────────────────────────────

class BadgePngView(APIView):
    """
    Serves the badge PNG. Public so a QR code on a printed certificate
    resolves even without a session.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, badge_id):
        badge = get_object_or_404(Badge, badge_id__iexact=badge_id)

        variant = request.query_params.get("variant", "plain")
        if variant == "with-qr":
            png_bytes = render_badge_with_qr_png_bytes(badge)
        else:
            png_bytes = render_badge_png_bytes(badge)

        from django.http import HttpResponse
        response = HttpResponse(png_bytes, content_type="image/png")
        response["Content-Disposition"] = f'inline; filename="{badge.badge_id}.png"'
        response["Cache-Control"] = "public, max-age=86400"
        return response


# ───────────────────────────── Admin: force issue ─────────────────────────────

class BadgeIssueView(APIView):
    """Admin-only manual issuance. Used in demos and backfills."""
    permission_classes = [IsAdminOrTemplateEditor]

    def post(self, request):
        serializer = BadgeIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.accounts.models import User
        from apps.courses.models import Course

        user = get_object_or_404(User, id=serializer.validated_data["user_id"])
        course = get_object_or_404(Course, id=serializer.validated_data["course_id"])

        badge = issue_badge(user, course, force=serializer.validated_data["force"])
        if badge is None:
            return Response(
                {"detail": "Course has badges disabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BadgeSerializer(badge, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


# ───────────────────────────── Admin: bulk revoke ─────────────────────────────

class BadgeRevokeView(APIView):
    permission_classes = [IsAdminOrTemplateEditor]

    def post(self, request, badge_id):
        badge = get_object_or_404(Badge, badge_id__iexact=badge_id)
        reason = request.data.get("reason", "")
        badge.revoke(reason=reason)
        return Response(BadgeSerializer(badge, context={"request": request}).data)


# ───────────────────────────── Admin: regenerate PNG ─────────────────────────────

class BadgeRegenerateView(APIView):
    """Regenerate the PNG after a template change."""
    permission_classes = [IsAdminOrTemplateEditor]

    def post(self, request, badge_id):
        badge = get_object_or_404(Badge, badge_id__iexact=badge_id)
        tasks.render_badge_png_task.delay(badge.id, overwrite=True)
        return Response({"detail": "PNG rendering queued."}, status=status.HTTP_202_ACCEPTED)