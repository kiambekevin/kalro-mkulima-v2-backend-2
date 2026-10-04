# apps/fielddays/models.py
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.common.models import TimeStampedModel
from .constants import (
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    BOOKING_STATUS_CONFIRMED,
    BOOKING_STATUS_WAITLISTED,
    BOOKING_STATUS_CANCELLED,
    BOOKING_STATUS_ATTENDED,
    BOOKING_STATUS_NO_SHOW,
    BOOKING_CODE_LENGTH,
)
from .managers import FieldDayManager, BookingManager
from .validators import validate_spots


# ───────────────────────────── FieldDay ─────────────────────────────

class FieldDay(TimeStampedModel):
    """
    A single in-person event: a field day, demonstration session, or
    group training. Shown in the dashboard, filterable by county and
    topic, and bookable by learners.
    """
    class Status(models.TextChoices):
        DRAFT     = STATUS_DRAFT,     "Draft"
        PUBLISHED = STATUS_PUBLISHED, "Published"
        CANCELLED = STATUS_CANCELLED, "Cancelled"
        COMPLETED = STATUS_COMPLETED, "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)

    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    topic = models.ForeignKey(
        "courses.Subject",
        on_delete=models.PROTECT, related_name="field_days",
    )

    # Location
    county = models.ForeignKey(
        "counties.County",
        on_delete=models.PROTECT, related_name="field_days",
    )
    venue = models.CharField(max_length=180)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )

    # Time
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField()
    timezone_name = models.CharField(max_length=40, default="Africa/Nairobi")

    # Capacity
    spots = models.PositiveSmallIntegerField(
        default=30, validators=[validate_spots],
    )
    waitlist_enabled = models.BooleanField(default=True)

    # People
    host = models.CharField(max_length=120, blank=True)
    host_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hosted_field_days",
        limit_choices_to={"role__in": ["trainer", "extension", "county", "admin"]},
    )
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    # Publishing
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True,
    )

    # Extras
    # cover_image_url = models.URLField(blank=True)
    cover_image_url = models.ImageField(upload_to="courses/images/", blank=True, null=True)
    notes = models.JSONField(default=list, blank=True)

    objects = FieldDayManager()

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["status", "starts_at"]),
            models.Index(fields=["county", "starts_at"]),
            models.Index(fields=["topic", "starts_at"]),
        ]
        verbose_name = "Field day"
        verbose_name_plural = "Field days"

    def __str__(self):
        return f"{self.title} · {self.county.name} · {self.starts_at:%d %b %Y}"

    # ── State helpers ────────────────────────────────────────────

    @property
    def is_upcoming(self) -> bool:
        return (
            self.status == self.Status.PUBLISHED
            and self.starts_at > timezone.now()
        )

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        return (
            self.status == self.Status.PUBLISHED
            and self.starts_at <= now <= self.ends_at
        )

    @property
    def is_past(self) -> bool:
        return self.ends_at < timezone.now()

    # ── Capacity helpers ─────────────────────────────────────────

    @property
    def booked_count(self) -> int:
        return self.bookings.filter(
            status__in=[BOOKING_STATUS_CONFIRMED, BOOKING_STATUS_ATTENDED]
        ).count()

    @property
    def attended_count(self) -> int:
        return self.bookings.filter(status=BOOKING_STATUS_ATTENDED).count()

    @property
    def waitlisted_count(self) -> int:
        return self.bookings.filter(status=BOOKING_STATUS_WAITLISTED).count()

    @property
    def spots_left(self) -> int:
        return max(0, self.spots - self.booked_count)

    @property
    def is_full(self) -> bool:
        return self.spots_left <= 0

    # ── State transitions ────────────────────────────────────────

    def publish(self, save: bool = True):
        self.status = self.Status.PUBLISHED
        if save:
            self.save(update_fields=["status", "updated_at"])
        return self

    def cancel(self, reason: str = "", save: bool = True):
        self.status = self.Status.CANCELLED
        if reason:
            self.notes = (self.notes or []) + [{"type": "cancel", "reason": reason}]
            if save:
                self.save(update_fields=["status", "notes", "updated_at"])
                return self
        if save:
            self.save(update_fields=["status", "updated_at"])
        return self


# ───────────────────────────── Booking ─────────────────────────────

class Booking(TimeStampedModel):
    """
    A learner's reservation for a field day. A single user can only
    hold one active booking per event.
    """
    class Status(models.TextChoices):
        CONFIRMED  = BOOKING_STATUS_CONFIRMED,  "Confirmed"
        WAITLISTED = BOOKING_STATUS_WAITLISTED, "Waitlisted"
        CANCELLED  = BOOKING_STATUS_CANCELLED,  "Cancelled"
        ATTENDED   = BOOKING_STATUS_ATTENDED,   "Attended"
        NO_SHOW    = BOOKING_STATUS_NO_SHOW,    "No-show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field_day = models.ForeignKey(
        FieldDay, on_delete=models.CASCADE, related_name="bookings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="field_day_bookings",
    )

    # Public code used for check-in QR and manual lookup
    code = models.CharField(
        max_length=12, unique=True, db_index=True, blank=True,
    )

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.CONFIRMED, db_index=True,
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Waitlist position is implicit — computed by ordering on booked_at
    objects = BookingManager()

    class Meta:
        ordering = ["booked_at"]
        unique_together = [("field_day", "user")]
        indexes = [
            models.Index(fields=["field_day", "status"]),
            models.Index(fields=["user", "status"]),
        ]
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"

    def __str__(self):
        return f"{self.user} → {self.field_day.title} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_code() -> str:
        """Human-friendly, unambiguous alphabet (no 0/O/1/I)."""
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            code = get_random_string(BOOKING_CODE_LENGTH, allowed_chars=alphabet)
            if not Booking.objects.filter(code=code).exists():
                return code

    # ── State helpers ────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.status in (self.Status.CONFIRMED, self.Status.WAITLISTED)

    @property
    def can_check_in(self) -> bool:
        now = timezone.now()
        fd = self.field_day
        return (
            self.status == self.Status.CONFIRMED
            and fd.starts_at - timezone.timedelta(minutes=60) <= now <= fd.ends_at + timezone.timedelta(minutes=120)
        )

    def cancel(self, save: bool = True):
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        if save:
            self.save(update_fields=["status", "cancelled_at", "updated_at"])
        return self


# ───────────────────────────── Attendance ─────────────────────────────

class Attendance(TimeStampedModel):
    """
    Physical check-in record. Created when a booking is validated at the
    venue (via QR scan or code entry by the field-day host).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="attendance",
    )
    checked_in_at = models.DateTimeField(auto_now_add=True, db_index=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="checkins_performed",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-checked_in_at"]
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"

    def __str__(self):
        return f"Check-in · {self.booking.user} @ {self.booking.field_day.title}"