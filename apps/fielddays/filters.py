# apps/fielddays/filters.py
import django_filters
from django.utils import timezone

from .models import FieldDay, Booking


class FieldDayFilter(django_filters.FilterSet):
    """
    Filter set matching the query params the React dashboard sends:
      county, topic, from, to, upcoming, q, status
    """
    q = django_filters.CharFilter(method="filter_search", label="Search")
    county = django_filters.CharFilter(field_name="county__name", lookup_expr="iexact")
    county_code = django_filters.CharFilter(field_name="county__code")
    topic = django_filters.CharFilter(field_name="topic__slug")
    upcoming = django_filters.BooleanFilter(method="filter_upcoming")
    past = django_filters.BooleanFilter(method="filter_past")
    from_date = django_filters.DateFilter(field_name="starts_at", lookup_expr="date__gte")
    to_date = django_filters.DateFilter(field_name="starts_at", lookup_expr="date__lte")

    class Meta:
        model = FieldDay
        fields = ["status", "county", "topic"]

    def filter_search(self, qs, name, value):
        value = value.strip()
        if not value:
            return qs
        return qs.filter(
            django_filters.utils.Q(title__icontains=value)
            | django_filters.utils.Q(description__icontains=value)
            | django_filters.utils.Q(venue__icontains=value)
        )

    def filter_upcoming(self, qs, name, value):
        if value:
            return qs.filter(starts_at__gte=timezone.now())
        return qs

    def filter_past(self, qs, name, value):
        if value:
            return qs.filter(ends_at__lt=timezone.now())
        return qs


class BookingFilter(django_filters.FilterSet):
    field_day = django_filters.UUIDFilter(field_name="field_day__id")
    field_day_slug = django_filters.CharFilter(field_name="field_day__slug")
    status = django_filters.CharFilter(field_name="status")
    user_email = django_filters.CharFilter(field_name="user__email", lookup_expr="iexact")

    class Meta:
        model = Booking
        fields = ["status", "field_day"]