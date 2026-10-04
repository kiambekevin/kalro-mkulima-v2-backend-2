# api/exceptions.py
"""
Thin alias around `apps.common.exceptions.api_exception_handler` so
DRF settings can reference `api.exceptions.api_exception_handler`.
Keeps the settings file decoupled from the `apps` package path.
"""
from apps.common.exceptions import (  # noqa: F401
    BusinessRuleError,
    ConflictError,
    GoneError,
    RateLimited,
    ServiceUnavailable,
    api_exception_handler,
)

# The handler DRF settings should point to
exception_handler = api_exception_handler