# apps/fielddays/services.py
"""
Business rules for booking, cancelling, checking in, and auto-promoting
waitlisted users when a spot opens up.
"""
import logging

from django.db import transaction
from django.utils import timezone

from .constants import (
    BOOKING_CUTOFF_MINUTES,
    CHECKIN_EARLY_MINUTES,
    CHECKIN_LATE_MINUTES,
    WAITLIST_EXPIRY_HOURS,
    BOOKING_STATUS_CONFIRMED,
    BOOKING_STATUS_WAITLISTED,
    BOOKING_STATUS_CANCELLED,
    BOOKING_STATUS_ATTENDED,
    BOOKING_STATUS_NO_SHOW,
)
from .models import FieldDay, Booking, Attendance

logger = logging.getLogger(__name__)


# ───────────────────────────── Exceptions ─────────────────────────────

class BookingError(Exception):
    """Raised when a booking request can't be fulfilled."""


class CheckinError(Exception):
    """Raised when a check-in can't be validated."""


# ───────────────────────────── Booking ─────────────────────────────

@transaction.atomic
def book_field_day(user, field_day: FieldDay) -> tuple[Booking, bool]:
    """
    Returns (booking, created).

    Rules:
      - Event must be published and in the future.
      - User can hold at most one active booking per event.
      - If full, user goes onto the waitlist when enabled.
      - Booking window closes BOOKING_CUTOFF_MINUTES after start.
    """
    now = timezone.now()

    if field_day.status != FieldDay.Status.PUBLISHED:
        raise BookingError("This field day is not open for booking.")

    if field_day.starts_at < now - timezone.timedelta(minutes=BOOKING_CUTOFF_MINUTES):
        raise BookingError("Booking has closed for this field day.")

    existing = Booking.objects.filter(user=user, field_day=field_day).first()
    if existing and existing.status in (BOOKING_STATUS_CONFIRMED, BOOKING_STATUS_WAITLISTED):
        return existing, False

    # Reactivate a cancelled booking
    if existing and existing.status == BOOKING_STATUS_CANCELLED:
        target_status = _target_status(field_day)
        existing.status = target_status
        existing.cancelled_at = None
        existing.save(update_fields=["status", "cancelled_at", "updated_at"])
        return existing, False

    target_status = _target_status(field_day)
    booking = Booking.objects.create(
        user=user,
        field_day=field_day,
        status=target_status,
    )
    logger.info(
        "Booked field day %s for %s (%s)",
        field_day.slug, user.email, target_status,
    )
    return booking, True


def _target_status(field_day: FieldDay) -> str:
    if field_day.is_full:
        if not field_day.waitlist_enabled:
            raise BookingError("This field day is full.")
        return BOOKING_STATUS_WAITLISTED
    return BOOKING_STATUS_CONFIRMED


@transaction.atomic
def cancel_booking(booking: Booking) -> Booking:
    """
    Cancels a booking and promotes the first waitlisted user if a
    confirmed spot opened up.
    """
    was_confirmed = booking.status == BOOKING_STATUS_CONFIRMED
    booking.cancel()

    if was_confirmed:
        _promote_next_waitlisted(booking.field_day)

    return booking


# ───────────────────────────── Waitlist ─────────────────────────────

def _promote_next_waitlisted(field_day: FieldDay) -> Booking | None:
    """
    Move the earliest waitlisted user up to confirmed if a spot is
    available. Called after any cancellation.
    """
    if field_day.is_full:
        return None

    next_up = (
        Booking.objects
        .filter(field_day=field_day, status=BOOKING_STATUS_WAITLISTED)
        .order_by("booked_at")
        .first()
    )
    if not next_up:
        return None

    next_up.status = BOOKING_STATUS_CONFIRMED
    next_up.save(update_fields=["status", "updated_at"])
    logger.info(
        "Promoted waitlisted booking %s for %s",
        next_up.code, next_up.user.email,
    )

    # Notify the promoted user (Celery)
    try:
        from .tasks import notify_promoted_booking
        notify_promoted_booking.delay(next_up.id)
    except Exception:  # noqa: BLE001
        pass

    return next_up


# ───────────────────────────── Check-in ─────────────────────────────

@transaction.atomic
def check_in_booking(*, booking: Booking, checked_in_by=None,
                     latitude=None, longitude=None, notes: str = "") -> Attendance:
    """
    Validate and record attendance. Rules:
      - Booking must be CONFIRMED (not waitlisted/cancelled/attended).
      - Current time must be within the check-in window.
    """
    if booking.status != BOOKING_STATUS_CONFIRMED:
        raise CheckinError(
            f"Cannot check in a booking with status '{booking.status}'."
        )

    now = timezone.now()
    fd = booking.field_day
    earliest = fd.starts_at - timezone.timedelta(minutes=CHECKIN_EARLY_MINUTES)
    latest = fd.ends_at + timezone.timedelta(minutes=CHECKIN_LATE_MINUTES)

    if now < earliest:
        raise CheckinError("Check-in hasn't opened yet.")

    if now > latest:
        raise CheckinError("Check-in window has closed.")

    attendance, created = Attendance.objects.get_or_create(
        booking=booking,
        defaults={
            "checked_in_by": checked_in_by,
            "latitude": latitude,
            "longitude": longitude,
            "notes": notes,
        },
    )

    if created:
        booking.status = BOOKING_STATUS_ATTENDED
        booking.save(update_fields=["status", "updated_at"])
        logger.info("Checked in booking %s for %s", booking.code, booking.user.email)

    return attendance


# ───────────────────────────── Status jobs ─────────────────────────────

@transaction.atomic
def close_past_events(reference=None) -> int:
    """
    Marks past events as COMPLETED and unattended confirmed bookings as
    NO_SHOW. Runs from a scheduled task.
    """
    reference = reference or timezone.now()
    events = FieldDay.objects.published().filter(ends_at__lt=reference)
    count = 0
    for fd in events:
        fd.status = FieldDay.Status.COMPLETED
        fd.save(update_fields=["status", "updated_at"])

        Booking.objects.filter(
            field_day=fd, status=BOOKING_STATUS_CONFIRMED,
        ).update(status=BOOKING_STATUS_NO_SHOW)
        count += 1

    logger.info("Closed %d past field day(s).", count)
    return count