# apps/counties/urls.py
"""
County URLs.

Every endpoint in this app is a ViewSet (CountyViewSet, SubCountyViewSet,
WardViewSet) registered on api/v1/routers.py. There are no custom
APIViews to declare here.

Kept as a file so apps have a consistent shape and future additions
(e.g. a county-level CSV export) have an obvious home.
"""
from django.urls import path  # noqa: F401

app_name = "counties"

# Intentionally empty. The router handles /api/v1/counties/,
# /api/v1/sub-counties/, and /api/v1/wards/.
urlpatterns = []