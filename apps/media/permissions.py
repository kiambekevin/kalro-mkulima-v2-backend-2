# apps/media/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .signing import verify_signed_url


class IsUploaderOrAdmin(BasePermission):
    """Object-level: only the uploader or an admin can delete/update an asset."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.uploaded_by_id == request.user.id


class HasValidSignature(BasePermission):
    """
    Grants access to media bytes only when the request carries a valid
    HMAC signature. Used by the download endpoint.

    The React app calls the API to get a signed URL, then hits that URL.
    A user pasting the plain URL into a browser is rejected.
    """

    def has_permission(self, request, view):
        full_url = request.build_absolute_uri()
        return verify_signed_url(full_url)


class CanUploadMedia(BasePermission):
    """Only trainers, researchers and admins can initiate uploads."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user.role in ("trainer", "researcher", "ngo")