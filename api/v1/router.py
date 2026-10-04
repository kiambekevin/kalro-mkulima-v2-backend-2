# api/v1/routers.py
"""
Central registration for every DRF ViewSet in the project.

Rule: only ViewSets go here. Custom APIViews (login, verify, check-in,
dashboard, uploads) belong in the corresponding app's urls.py.

Modules and lessons are declared as nested paths in
`apps/courses/urls.py`, so they are NOT registered here — that would
create duplicate URLs.
"""
from rest_framework.routers import DefaultRouter

from apps.badges.views import BadgeTemplateViewSet, MyBadgesViewSet
from apps.counties.views import CountyViewSet, SubCountyViewSet, WardViewSet
from apps.courses.views import CourseViewSet, PathwayViewSet, SubjectViewSet
from apps.fielddays.views import FieldDayViewSet, MyBookingsViewSet
from apps.progress.views import MyProgressViewSet

router = DefaultRouter(trailing_slash=True)

# ── Courses & curriculum ────────────────────────────────────────
router.register("subjects", SubjectViewSet, basename="subject")
router.register("courses", CourseViewSet, basename="course")

# ── Progress ────────────────────────────────────────────────────
router.register("progress", MyProgressViewSet, basename="progress")

# ── Badges ──────────────────────────────────────────────────────
router.register("badges", MyBadgesViewSet, basename="badge")
router.register("badge-templates", BadgeTemplateViewSet, basename="badge-template")

# ── Field days ──────────────────────────────────────────────────
router.register("fielddays", FieldDayViewSet, basename="fieldday")
router.register("fielddays/my-bookings", MyBookingsViewSet, basename="my-booking")

# ── Counties ────────────────────────────────────────────────────
router.register("counties", CountyViewSet, basename="county")
router.register("sub-counties", SubCountyViewSet, basename="subcounty")
router.register("wards", WardViewSet, basename="ward")

# ── Pathways ────────────────────────────────────────────────────
router.register("pathways", PathwayViewSet, basename="pathway")

urlpatterns = router.urls




# …

