# apps/counties/filters.py
import django_filters

from .models import County, SubCounty, Ward


class CountyFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="Search")
    region = django_filters.CharFilter(field_name="region", lookup_expr="iexact")
    code = django_filters.CharFilter(field_name="code", lookup_expr="exact")

    class Meta:
        model = County
        fields = ["region", "code"]

    def filter_search(self, qs, name, value):
        value = value.strip()
        if not value:
            return qs
        return qs.filter(
            django_filters.utils.Q(name__icontains=value)
            | django_filters.utils.Q(code__icontains=value)
            | django_filters.utils.Q(region__icontains=value)
        )


class SubCountyFilter(django_filters.FilterSet):
    county = django_filters.CharFilter(field_name="county__code")
    county_name = django_filters.CharFilter(field_name="county__name", lookup_expr="iexact")

    class Meta:
        model = SubCounty
        fields = ["county"]


class WardFilter(django_filters.FilterSet):
    sub_county = django_filters.UUIDFilter(field_name="sub_county__id")
    county = django_filters.CharFilter(field_name="sub_county__county__code")

    class Meta:
        model = Ward
        fields = ["sub_county", "county"]