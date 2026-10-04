# api/routers.py
"""
Custom DefaultRouter subclass.

Adds:
  - `.json` format suffix on every URL
  - a stable `basename` convention
  - a versioned prefix (`/api/v1/...`) applied by the caller
"""
from rest_framework.routers import DefaultRouter


class APIRouter(DefaultRouter):
    """
    DefaultRouter with format suffixes so clients can request
    `/api/v1/courses.json` if they prefer a file extension.
    """
    include_format_suffixes = True
    trailing_slash = "/"


class NestedRouter(APIRouter):
    """
    Marker class reserved for future nested routes. Kept as a subclass
    so imports stay stable when nesting is added later.
    """