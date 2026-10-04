# apps/fielddays/managers.py
from django.db import models
from django.utils import timezone


class FieldDayQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status="published")

    def upcoming(self):
        return self.published().filter(starts_at__gte=timezone.now())

    def past(self):
        return self.published().filter(ends_at__lt=timezone.now())

    def in_county(self, county_id_or_name):
        if hasattr(county_id_or_name, "pk"):
            return self.filter(county=county_id_or_name)
        return self.filter(
            models.Q(county__code=county_id_or_name)
            | models.Q(county__name__iexact=county_id_or_name)
        )

    def by_topic(self, subject_slug):
        return self.filter(topic__slug=subject_slug)

    def with_attendance_counts(self):
        return self.annotate(
            booked_count=models.Count(
                "bookings",
                filter=models.Q(bookings__status__in=["confirmed", "attended"]),
            ),
            attended_count=models.Count(
                "bookings",
                filter=models.Q(bookings__status="attended"),
            ),
        )


class FieldDayManager(models.Manager.from_queryset(FieldDayQuerySet)):
    pass


class BookingQuerySet(models.QuerySet):
    def confirmed(self):
        return self.filter(status="confirmed")

    def attended(self):
        return self.filter(status="attended")

    def for_user(self, user):
        return self.filter(user=user)

    def for_event(self, field_day):
        return self.filter(field_day=field_day)


class BookingManager(models.Manager.from_queryset(BookingQuerySet)):
    pass