# apps/analytics/urls.py
from django.urls import path

from .views import TrackVisitView, VisitStatsView

app_name = "analytics"

urlpatterns = [
    path("analytics/track/", TrackVisitView.as_view(), name="track"),
    path("analytics/visits/", VisitStatsView.as_view(), name="visits"),
]