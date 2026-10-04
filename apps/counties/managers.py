# apps/counties/managers.py
from django.db import models


class CountyQuerySet(models.QuerySet):
    def with_sub_county_count(self):
        return self.annotate(
            sub_county_count=models.Count("sub_counties", distinct=True),
        )

    def with_user_count(self):
        return self.annotate(
            user_count=models.Count("users", distinct=True),
        )

    def by_region(self, region: str):
        return self.filter(region__iexact=region)

    def with_dashboard_data(self):
        """
        Attach the aggregates the county dashboard needs in one query.
        """
        return self.annotate(
            user_count=models.Count("users", distinct=True),
            field_day_count=models.Count("field_days", distinct=True),
        )


class CountyManager(models.Manager.from_queryset(CountyQuerySet)):
    pass


class SubCountyQuerySet(models.QuerySet):
    def for_county(self, county_code_or_id):
        if hasattr(county_code_or_id, "pk"):
            return self.filter(county=county_code_or_id)
        return self.filter(county__code=county_code_or_id)


class SubCountyManager(models.Manager.from_queryset(SubCountyQuerySet)):
    pass


class WardQuerySet(models.QuerySet):
    def for_sub_county(self, sub_county_id):
        return self.filter(sub_county_id=sub_county_id)


class WardManager(models.Manager.from_queryset(WardQuerySet)):
    pass