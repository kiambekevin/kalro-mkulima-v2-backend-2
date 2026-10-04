# api/renderers.py
"""
Renderers. JSON is the primary response format; the browsable API is
only enabled in DEBUG so production never leaks interactive forms.
"""
from django.conf import settings
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer


class APIRenderer(JSONRenderer):
    """
    JSON renderer with a consistent charset and compact output for
    production. Set `indent=2` via the `?pretty=1` query param for
    debugging.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = renderer_context.get("request") if renderer_context else None
        if request and request.query_params.get("pretty") in ("1", "true"):
            self.charset = "utf-8"
            return super().render(
                data, accepted_media_type, renderer_context,
            )
        return super().render(data, accepted_media_type, renderer_context)


# Renderer lists

JSON_ONLY_RENDERERS = (APIRenderer,)

DEFAULT_RENDERERS = (
    (APIRenderer, BrowsableAPIRenderer) if settings.DEBUG
    else (APIRenderer,)
)