# apps/fielddays/tasks.py
"""
Celery jobs for reminders, waitlist expiry, notifications.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .constants import REMINDER_WINDOWS_HOURS, WAITLIST_EXPIRY_HOURS
from .models import Booking, FieldDay

logger = logging.getLogger(__name__)


@shared_task
def send_upcoming_reminders():
    """
    Runs hourly. Sends SMS/email reminders for events starting within
    the configured reminder windows (48h, 24h, 2h).
    """
    from apps.notifications.services import send_sms, send_email

    now = timezone.now()
    sent = 0

    for hours in REMINDER_WINDOWS_HOURS:
        window_start = now + timezone.timedelta(hours=hours - 1)
        window_end = now + timezone.timedelta(hours=hours)
        events = FieldDay.objects.published().filter(
            starts_at__gte=window_start, starts_at__lt=window_end,
        )

        for fd in events:
            bookings = fd.bookings.filter(status="confirmed").select_related("user")
            for booking in bookings:
                user = booking.user
                message = (
                    f"Reminder: '{fd.title}' starts in ~{hours}h at {fd.venue}, "
                    f"{fd.county.name}. Your code: {booking.code}."
                )
                if user.phone:
                    send_sms(str(user.phone), message)
                if user.email:
                    send_email(
                        to=user.email,
                        subject=f"Reminder: {fd.title}",
                        body=message,
                    )
                sent += 1

    logger.info("Sent %d field-day reminder(s).", sent)
    return sent


@shared_task
def notify_promoted_booking(booking_id):
    """
    Called when a waitlisted booking is moved to confirmed because a
    spot opened up.
    """
    from apps.notifications.services import send_sms

    try:
        booking = Booking.objects.select_related("user", "field_day").get(id=booking_id)
    except Booking.DoesNotExist:
        return

    user = booking.user
    fd = booking.field_day
    message = (
        f"Good news! A spot opened up for '{fd.title}' on "
        f"{fd.starts_at:%d %b, %H:%M}. Your code: {booking.code}."
    )
    if user.phone:
        send_sms(str(user.phone), message)


@shared_task
def expire_stale_waitlist_entries():
    """
    If a waitlisted user is promoted but doesn't confirm within
    WAITLIST_EXPIRY_HOURS, drop them and promote the next person.
    """
    cutoff = timezone.now() - timezone.timedelta(hours=WAITLIST_EXPIRY_HOURS)
    stale = Booking.objects.filter(
        status="waitlisted",
        booked_at__lt=cutoff,
    )
    count = stale.update(status="cancelled", cancelled_at=timezone.now())
    logger.info("Expired %d stale waitlist entries.", count)
    return count


@shared_task
def close_past_field_days():
    """Scheduled daily — delegates to the service function."""
    from .services import close_past_events
    return close_past_events()