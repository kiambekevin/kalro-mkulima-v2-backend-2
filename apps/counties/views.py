# apps/counties/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .filters import CountyFilter, SubCountyFilter, WardFilter
from .models import County, SubCounty, Ward
from .permissions import ReadOnlyOrStaff
from .selectors import (
    all_counties_with_counts,
    county_by_code,
    sub_counties_for_county,
)
from .serializers import (
    CountySerializer,
    CountyCompactSerializer,
    CountyDashboardSerializer,
    SubCountySerializer,
    SubCountyCompactSerializer,
    WardSerializer,
)


class CountyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    County reference data.
      GET /api/v1/counties/                    → list (compact)
      GET /api/v1/counties/{code}/             → detail with sub-counties
      GET /api/v1/counties/{code}/sub-counties/
      GET /api/v1/counties/{code}/dashboard/   → aggregates for county officers
      GET /api/v1/counties/regions/            → list of regions with counts
    """
    queryset = County.objects.all()
    permission_classes = [AllowAny, ReadOnlyOrStaff]
    filterset_class = CountyFilter
    lookup_field = "code"
    search_fields = ["code", "name", "region"]
    ordering_fields = ["code", "name", "region"]

    def get_serializer_class(self):
        if self.action == "list":
            return CountyCompactSerializer
        if self.action == "dashboard":
            return CountyDashboardSerializer
        return CountySerializer

    def get_queryset(self):
        if self.action == "list":
            return County.objects.all().order_by("code")
        return County.objects.all()

    def get_object(self):
        code = self.kwargs["code"]
        county = county_by_code(code)
        if not county:
            from django.http import Http404
            raise Http404
        return county

    # ── Custom actions ──────────────────────────────────────────

    @action(detail=True, methods=["get"], permission_classes=[AllowAny], url_path="sub-counties")
    def sub_counties(self, request, code=None):
        qs = sub_counties_for_county(code)
        return Response(SubCountyCompactSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def regions(self, request):
        from django.db.models import Count
        rows = (
            County.objects
            .values("region")
            .annotate(count=Count("id"))
            .order_by("region")
        )
        return Response([{"region": r["region"], "counties": r["count"]} for r in rows])

    @action(detail=True, methods=["get"])
    def dashboard(self, request, code=None):
        """
        Lightweight county dashboard — user count, field day count.
        The full county dashboard lives at /api/v1/dashboard/county/{code}/.
        """
        county = self.get_object()
        county = County.objects.with_dashboard_data().get(pk=county.pk)
        return Response(CountyDashboardSerializer(county).data)


class SubCountyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Sub-county reference data.
      GET /api/v1/sub-counties/?county=032
      GET /api/v1/sub-counties/{id}/
    """
    queryset = SubCounty.objects.select_related("county").all()
    serializer_class = SubCountySerializer
    permission_classes = [AllowAny, ReadOnlyOrStaff]
    filterset_class = SubCountyFilter
    search_fields = ["name", "county__name", "county__code"]

    def get_serializer_class(self):
        if self.action == "list":
            return SubCountyCompactSerializer
        return SubCountySerializer


class WardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Ward reference data.
      GET /api/v1/wards/?county=032
      GET /api/v1/wards/?sub_county={id}
    """
    queryset = Ward.objects.select_related("sub_county", "sub_county__county").all()
    serializer_class = WardSerializer
    permission_classes = [AllowAny, ReadOnlyOrStaff]
    filterset_class = WardFilter
    search_fields = ["name", "sub_county__name", "sub_county__county__name"]