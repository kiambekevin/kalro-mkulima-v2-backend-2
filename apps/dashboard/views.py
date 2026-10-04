# apps/dashboard/views.py
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.counties.models import County

from . import cache as dash_cache
from .permissions import CanViewCountyDashboard
from .services import build_county_dashboard, build_learner_dashboard


class LearnerDashboardView(APIView):
    """
    GET /api/v1/dashboard/
    Returns the aggregated learner dashboard payload. Pass ?refresh=true
    to skip the cache (useful right after a lesson is completed).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        use_cache = request.query_params.get("refresh") != "true"
        if not use_cache:
            dash_cache.invalidate_learner(request.user.id)

        # Updated use_cache=use_cache to honor ?refresh=true
        payload = build_learner_dashboard(request.user, use_cache=use_cache)
        return Response(payload)


class CountyDashboardView(APIView):
    """
    GET /api/v1/dashboard/county/{code}/
    County officers and admins only. Returns aggregate stats.
    """
    permission_classes = [IsAuthenticated, CanViewCountyDashboard]

    def get(self, request, code):
        county = get_object_or_404(County, code=code)
        self.check_object_permissions(request, county)

        use_cache = request.query_params.get("refresh") != "true"
        if not use_cache:
            dash_cache.invalidate_county(county.id)

        payload = build_county_dashboard(county, use_cache=use_cache)
        return Response(payload)


class DashboardRefreshView(APIView):
    """
    POST /api/v1/dashboard/refresh/
    Manually invalidates the caller's cached dashboard. The next GET
    rebuilds it. Useful after bulk actions (imports, refunds).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        dash_cache.invalidate_learner(request.user.id)
        if request.user.is_staff:
            dash_cache.invalidate_all()
        return Response({"detail": "Dashboard cache cleared."})