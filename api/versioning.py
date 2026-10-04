# api/versioning.py
"""
API versioning strategy: URL path prefix.

    /api/v1/courses/     →  v1
    /api/v2/courses/     →  v2

`request.version` is set by DRF's URLPathVersioning and can be used in
views to branch behaviour without duplicating the URL config.
"""
from rest_framework.versioning import URLPathVersioning


class DefaultVersioning(URLPathVersioning):
    default_version = "v1"
    allowed_versions = ["v1", "v2"]
    version_param = "version"
    invalid_version_message = "Unsupported API version."