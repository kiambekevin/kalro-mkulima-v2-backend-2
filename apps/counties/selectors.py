# apps/counties/selectors.py
from django.db.models import Prefetch

from .models import County, SubCounty, Ward


def all_counties_with_counts():
    return County.objects.with_sub_county_count().with_user_count().order_by("code")


def county_by_code(code: str):
    return (
        County.objects
        .filter(code=code)
        .prefetch_related(
            Prefetch(
                "sub_counties",
                queryset=SubCounty.objects.order_by("name").prefetch_related(
                    Prefetch("wards", queryset=Ward.objects.order_by("name")),
                ),
            ),
        )
        .first()
    )


def county_by_name(name: str):
    return County.objects.filter(name__iexact=name).first()


def counties_for_region(region: str):
    return County.objects.by_region(region).order_by("code")


def sub_counties_for_county(county_code: str):
    return (
        SubCounty.objects
        .for_county(county_code)
        .prefetch_related("wards")
        .order_by("name")
    )


def wards_for_sub_county(sub_county_id):
    return Ward.objects.for_sub_county(sub_county_id).order_by("name")