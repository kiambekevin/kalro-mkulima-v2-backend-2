# apps/accounts/models.py
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from apps.common.models import TimeStampedModel
from .constants import KENYAN_PHONE_REGEX
from .managers import UserManager


kenyan_phone_validator = RegexValidator(
    regex=KENYAN_PHONE_REGEX,
    message="Enter a valid Kenyan phone number (e.g. 0712 345 678).",
)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Primary user model for the platform. Every learner, trainer, extension
    officer and admin is one of these.
    """

    class Role(models.TextChoices):
        FARMER      = "farmer",      "Farmer"
        AGRIPRENEUR = "agripreneur", "Agripreneur"
        EXTENSION   = "extension",   "Extension officer"
        TRAINER     = "trainer",     "Lead farmer / Trainer"
        STUDENT     = "student",     "Student"
        RESEARCHER  = "researcher",  "Researcher"
        NGO         = "ngo",         "NGO / Partner"
        COUNTY      = "county",      "County officer"
        ADMIN       = "admin",       "Administrator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identity
    email = models.EmailField(unique=True, db_index=True)
    phone = PhoneNumberField(unique=True, region="KE")
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)

    # Roles & preferences
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.FARMER, db_index=True
    )
    preferred_language = models.CharField(
        max_length=4,
        choices=[("en", "English"), ("sw", "Kiswahili")],
        default="en",
    )

    # Status flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False, help_text="Set once the email or phone is verified."
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    # ── Convenience properties ────────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def display_name(self) -> str:
        return self.first_name or self.email.split("@")[0]

    @property
    def initials(self) -> str:
        first = (self.first_name or self.email)[0]
        last = (self.last_name or "")[:1]
        return (first + last).upper()

    @property
    def is_trainer(self) -> bool:
        return self.role in {self.Role.TRAINER, self.Role.ADMIN}

    @property
    def is_county_officer(self) -> bool:
        return self.role == self.Role.COUNTY

    @property
    def is_admin(self) -> bool:
        return self.is_staff or self.role == self.Role.ADMIN

    def touch_last_seen(self):
        """Called on each authenticated request by the middleware."""
        self.last_seen_at = timezone.now()
        self.save(update_fields=["last_seen_at"])


class Profile(TimeStampedModel):
    """
    Extended learner profile: location, farming interests and preferences.
    Kept separate from User so auth lookups stay lightweight.
    """

    class Gender(models.TextChoices):
        FEMALE  = "female",     "Female"
        MALE    = "male",       "Male"
        OTHER   = "other",      "Other"
        NOT_SAY = "prefer-not", "Prefer not to say"

    class Channel(models.TextChoices):
        APP = "app", "Mobile app"
        SMS = "sms", "SMS"
        WEB = "web", "Web browser"
        USD = "usd", "Field / USD"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )

    # Personal
    gender = models.CharField(max_length=12, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=20, blank=True)

    # Location — county is a FK to the counties app (nullable so we can
    # tolerate users who register before the county fixture is loaded).
    county = models.ForeignKey(
        "counties.County",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    sub_county = models.CharField(max_length=80, blank=True)
    ward = models.CharField(max_length=80, blank=True)

    # Farming profile
    value_chains = models.ManyToManyField(
        "courses.Subject", blank=True, related_name="interested_users"
    )
    acreage = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    group_name = models.CharField(max_length=120, blank=True)
    group_size = models.CharField(max_length=20, blank=True)

    # Preferences
    preferred_channel = models.CharField(
        max_length=12, choices=Channel.choices, default=Channel.APP
    )
    consent_data = models.BooleanField(default=False)
    consent_updates = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return f"Profile of {self.user.email}"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def is_youth(self) -> bool:
        """Youth is defined as 18–35 in Kenya's agricultural programs."""
        age = self.age
        return age is not None and 18 <= age <= 35