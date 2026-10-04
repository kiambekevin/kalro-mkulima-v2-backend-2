# apps/common/mixins.py
"""
ViewSet and admin mixins shared across apps.
"""
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response


class SoftDeleteViewSetMixin:
    """
    Adds `soft_delete` and `restore` actions to a DRF ViewSet whose
    queryset models inherit from SoftDeleteModel.
    """

    @action(detail=True, methods=["post"], url_path="soft-delete")
    def soft_delete(self, request, pk=None):
        obj = self.get_object()
        obj.delete()  # soft by default
        return Response({"detail": "Moved to trash."})

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        obj = self.get_object()
        obj.restore()
        return Response({"detail": "Restored."})


class PublishViewSetMixin:
    """
    Adds `publish` and `unpublish` actions to any ViewSet whose queryset
    models inherit from PublishableModel.
    """

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        obj = self.get_object()
        obj.publish()
        return Response({"detail": "Published."})

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        obj = self.get_object()
        obj.unpublish()
        return Response({"detail": "Unpublished."})


class AuditMixin:
    """
    Auto-fills `created_by` / `updated_by` on model save when the model
    has those fields. Call `self._set_audit_user(serializer)` inside
    `perform_create` and `perform_update`.
    """

    def _set_audit_user(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        if user is None:
            serializer.save()
            return
        instance = getattr(serializer, "instance", None)
        if instance is None:
            serializer.save(created_by=user, updated_by=user)
        else:
            serializer.save(updated_by=user)


class TimeStampedAdminMixin:
    """
    Admin mixin that shows `created_at` / `updated_at` as read-only.
    """
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "updated_at"):
            obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)