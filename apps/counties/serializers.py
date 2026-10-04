# apps/counties/serializers.py
from rest_framework import serializers

from .models import County, SubCounty, Ward


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ["id", "name", "code"]
        read_only_fields = fields


class SubCountySerializer(serializers.ModelSerializer):
    wards = WardSerializer(many=True, read_only=True)

    class Meta:
        model = SubCounty
        fields = ["id", "name", "code", "wards"]
        read_only_fields = fields


class SubCountyCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCounty
        fields = ["id", "name", "code"]
        read_only_fields = fields


class CountySerializer(serializers.ModelSerializer):
    """
    Full county representation including nested sub-counties.
    """
    sub_counties = SubCountySerializer(many=True, read_only=True)
    sub_county_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = County
        fields = [
            "id", "code", "name", "region", "slug",
            "capital", "area_km2", "population_2019", "icon",
            "sub_counties", "sub_county_count",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CountyCompactSerializer(serializers.ModelSerializer):
    """
    Small payload used in user profiles, field days, and dashboard
    summaries — just enough to render a name and code.
    """
    class Meta:
        model = County
        fields = ["id", "code", "name", "region", "slug"]
        read_only_fields = fields


class CountyDashboardSerializer(serializers.ModelSerializer):
    """
    Payload for `/counties/{code}/dashboard/`. Aggregates are computed
    by `apps.dashboard.services.build_county_dashboard`.
    """
    user_count = serializers.IntegerField(read_only=True, required=False)
    field_day_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = County
        fields = [
            "id", "code", "name", "region",
            "user_count", "field_day_count",
            "population_2019", "area_km2",
        ]
        read_only_fields = fields