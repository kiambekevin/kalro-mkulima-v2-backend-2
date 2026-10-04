"""
OpenAPI schema configuration for drf-spectacular.

- Adds tags per domain app
- Documents the auth flow (JWT bearer)
- Adds a shared error schema used by the exception handler
- Exposes a custom `SchemaGenerator` with sensible defaults
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication


# ───────────────────────────── Auth scheme ─────────────────────────────

class JWTScheme(OpenApiAuthenticationExtension):
    target_class = "rest_framework_simplejwt.authentication.JWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste the `access` token from /api/v1/auth/token/.",
        }


# ───────────────────────────── Errors ─────────────────────────────

ERROR_SCHEMA = OpenApiResponse(
    description="Standard error envelope",
    response={
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                    "detail": {"type": "object", "nullable": True},
                    "fields": {"type": "object"},
                },
            },
        },
    },
)


# ───────────────────────────── AutoSchema ─────────────────────────────

class KalroAutoSchema(AutoSchema):
    """
    AutoSchema with a couple of project-specific defaults:
      - Every operation is tagged by the app label of its view
      - The standard error schema is attached as a default response
    """

    def get_tags(self, path, method):
        tags = super().get_tags(path, method)
        if tags:
            return tags
        # Fall back to the first path segment
        segment = path.strip("/").split("/")[0] or "default"
        return [segment.replace("-", " ").title()]

    def _get_error_responses(self):
        return {
            400: ERROR_SCHEMA,
            401: ERROR_SCHEMA,
            403: ERROR_SCHEMA,
            404: ERROR_SCHEMA,
            500: ERROR_SCHEMA,
        }

    def get_response(self, path, method):
        response = super().get_response(path, method)
        # Merge our error responses into the success response
        if isinstance(response, dict):
            for status, schema in self._get_error_responses().items():
                response.setdefault(status, schema)
        return response


# ───────────────────────────── SPECTACULAR_SETTINGS ─────────────────────────────

SPECTACULAR_SETTINGS = {
    "TITLE": "KALRO Mkulima API",
    "DESCRIPTION": (
        "Free online and offline agricultural training for Kenya. "
        "Built by KALRO to support farmers, extension officers and agripreneurs "
        "with practical, research-backed content."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
    },
    "REDOC_UI_SETTINGS": {
        "hideDownloadButton": False,
        "theme": {"colors": {"primary": {"main": "#23804A"}}},
    },
    "TAGS": [
        {"name": "Auth", "description": "Registration, login, JWT, profile"},
        {"name": "Courses", "description": "Catalogue, curriculum, lessons"},
        {"name": "Progress", "description": "Lesson completion and streaks"},
        {"name": "Badges", "description": "Issuance and public verification"},
        {"name": "Field Days", "description": "In-person events and check-in"},
        {"name": "Dashboard", "description": "Aggregated learner and county dashboards"},
        {"name": "Media", "description": "Video manifests, PDFs, signed URLs"},
        {"name": "Counties", "description": "Reference data for Kenya's 47 counties"},
        {"name": "Notifications", "description": "SMS, email and push"},
        {"name": "Reports", "description": "County and partner exports"},
    ],
    "DEFAULT_AUTO_SCHEMA_CLASS": "api.schema.KalroAutoSchema",
}