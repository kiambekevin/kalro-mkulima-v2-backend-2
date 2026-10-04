# apps/fielddays/urls.py
"""
Field-day URLs that aren't ViewSets.

The `FieldDayViewSet` (list, detail, book, cancel, publish, bookings)
and `MyBookingsViewSet` are registered on api/v1/routers.py. This file
only declares:
  - host check-in endpoint (`POST /fielddays/checkin/`)
  - attendance list (`GET /fielddays/{slug}/attendance/`)
"""
from django.urls import path

from .views import AttendanceListView, CheckinView

app_name = "fielddays"

urlpatterns = [
    # ── Check-in (host / extension officer) ───────────────────
    # POST /api/v1/fielddays/checkin/
    # Body: { code, latitude?, longitude?, notes? }
    path("fielddays/checkin/", CheckinView.as_view(), name="checkin"),

    # ── Attendance list for a specific event ──────────────────
    # GET /api/v1/fielddays/{slug}/attendance/
    path(
        "fielddays/<slug:slug>/attendance/",
        AttendanceListView.as_view(),
        name="attendance",
    ),
]