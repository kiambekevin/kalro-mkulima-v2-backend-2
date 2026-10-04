# apps/fielddays/selectors.py
from django.db.models import Prefetch
from django.utils import timezone

from .models import FieldDay, Booking, Attendance


def upcoming_field_days(*, county=None, limit: int = 5):
    """
    Used by the dashboard 'Upcoming field days' panel.
    Prefers events in the user's county when provided.
    """
    qs = (
        FieldDay.objects
        .upcoming()
        .select_related("county", "topic")
        .with_attendance_counts()
    )
    if county:
        qs = qs.filter(county=county)
    return qs.order_by("starts_at")[:limit]


def field_day_by_slug(slug: str):
    return (
        FieldDay.objects
        .select_related("county", "topic", "host_user")
        .with_attendance_counts()
        .filter(slug=slug)
        .first()
    )


def bookings_for_field_day(field_day: FieldDay):
    return (
        Booking.objects
        .filter(field_day=field_day)
        .select_related("user")
        .prefetch_related(
            Prefetch("attendance", queryset=Attendance.objects.all()),
        )
    )


def bookings_for_user(user):
    return (
        Booking.objects
        .filter(user=user)
        .select_related("field_day", "field_day__county", "field_day__topic")
        .order_by("-booked_at")
    )


def booking_by_code(code: str):
    return (
        Booking.objects
        .select_related("user", "field_day", "field_day__county")
        .filter(code__iexact=code)
        .first()
    )


def waitlist_position(field_day: FieldDay, booking: Booking) -> int:
    """
    1-based position in the waitlist, or 0 if the booking isn't waitlisted.
    """
    if booking.status != "waitlisted":
        return 0
    qs = Booking.objects.filter(
        field_day=field_day, status="waitlisted", booked_at__lt=booking.booked_at,
    )
    return qs.count() + 1