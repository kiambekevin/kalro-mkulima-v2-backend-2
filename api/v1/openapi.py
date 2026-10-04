# api/v1/openapi.py
"""
Customisations applied to the OpenAPI schema on top of
`api/schema.py`. Called from the schema generation views.
"""
from drf_spectacular.utils import extend_schema


def apply_public_endpoints(schema):
    """
    Iterate operations and stamp public endpoints with
    `security: []` so the Swagger UI doesn't require auth for them.
    """
    public_prefixes = (
        "/api/v1/courses/",
        "/api/v1/subjects/",
        "/api/v1/counties/",
        "/api/v1/fielddays/",
        "/api/v1/badges/verify/",
    )
    public_exact = {
        "/api/v1/auth/register/",
        "/api/v1/auth/login/",
        "/api/v1/auth/token/",
        "/api/v1/auth/token/refresh/",
        "/api/v1/auth/check/email/",
        "/api/v1/auth/check/phone/",
    }

    for path, methods in schema.get("paths", {}).items():
        is_public = path in public_exact or any(path.startswith(p) for p in public_prefixes)
        if not is_public:
            continue
        for _, op in methods.items():
            if isinstance(op, dict):
                op.setdefault("security", [])

    return schema