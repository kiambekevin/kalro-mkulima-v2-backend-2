# apps/common/exceptions.py
"""
Custom exceptions and a DRF exception handler that returns a
consistent error envelope across the whole API.
"""
import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404

logger = logging.getLogger(__name__)


# ────────────────────────────── Custom exceptions ──────────────────────────────

class BusinessRuleError(APIException):
    """Generic 400 for domain-rule violations."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This action cannot be performed."
    default_code = "business_rule"


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflicting resource already exists."
    default_code = "conflict"


class GoneError(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = "This resource is no longer available."
    default_code = "gone"


class RateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests. Try again shortly."
    default_code = "rate_limited"


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The service is temporarily unavailable."
    default_code = "service_unavailable"


# ────────────────────────────── Handler ──────────────────────────────

def api_exception_handler(exc, context):
    """
    Wraps DRF's default handler to:
      - normalise `DjangoValidationError` into DRF's shape
      - return a consistent top-level envelope:
            { "error": { "code", "message", "detail", "fields" } }
      - log 5xx errors with request context
    """
    if isinstance(exc, DjangoValidationError):
        exc = _django_validation_to_drf(exc)

    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    detail = response.data
    message = _extract_message(detail)
    fields = _extract_fields(detail)

    envelope = {
        "error": {
            "code": _extract_code(exc),
            "message": message,
            "detail": detail if isinstance(detail, (dict, list)) else None,
            "fields": fields,
        }
    }

    # Log 5xx
    if response.status_code >= 500:
        request = context.get("request")
        logger.exception(
            "API error %s on %s %s",
            response.status_code,
            getattr(request, "method", "-"),
            getattr(request, "path", "-"),
            exc_info=exc,
        )

    response.data = envelope
    return response


def _django_validation_to_drf(exc: DjangoValidationError):
    from rest_framework.exceptions import ValidationError as DRFValidationError

    if hasattr(exc, "message_dict"):
        return DRFValidationError(detail=exc.message_dict)
    return DRFValidationError(detail=exc.messages)


def _extract_message(detail) -> str:
    if isinstance(detail, list) and detail:
        return str(detail[0])
    if isinstance(detail, dict):
        if "detail" in detail:
            return str(detail["detail"])
        first_key = next(iter(detail), None)
        if first_key is not None:
            value = detail[first_key]
            if isinstance(value, list) and value:
                return f"{first_key}: {value[0]}"
            return f"{first_key}: {value}"
    return str(detail)


def _extract_fields(detail) -> dict:
    if not isinstance(detail, dict):
        return {}
    return {k: v for k, v in detail.items() if k != "detail"}


def _extract_code(exc) -> str:
    return getattr(exc, "default_code", exc.__class__.__name__.lower())