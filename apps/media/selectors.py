# apps/media/selectors.py
from .models import MediaAsset, UploadSession


def asset_by_id(asset_id):
    return (
        MediaAsset.objects
        .select_related("uploaded_by")
        .filter(id=asset_id)
        .first()
    )


def asset_by_slug(slug: str):
    return (
        MediaAsset.objects
        .select_related("uploaded_by")
        .filter(slug=slug)
        .first()
    )


def assets_for_user(user):
    return MediaAsset.objects.for_uploader(user).order_by("-created_at")


def ready_video_assets():
    return MediaAsset.objects.videos().ready()


def ready_pdf_assets():
    return MediaAsset.objects.pdfs().ready()


def expired_upload_sessions():
    from django.utils import timezone
    return UploadSession.objects.filter(
        completed_at__isnull=True,
        expires_at__lt=timezone.now(),
    )