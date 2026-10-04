# apps/courses/models.py
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel
from .constants import (
    MIN_LESSONS_PER_COURSE,
    MAX_LESSONS_PER_COURSE,
    MAX_MODULES_PER_COURSE,
    DEFAULT_LESSON_MINUTES,
    RESOURCE_KINDS,
)
from .managers import SubjectManager, CourseManager, LessonManager
from .validators import validate_positive_minutes, validate_lesson_stream_url


# ───────────────────────────── Subject ─────────────────────────────

class Subject(TimeStampedModel):
    """
    Top-level taxonomy: Crops, Livestock, Water & Irrigation, etc.
    Mirrors `subjects` in src/data/courses.js.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=40, unique=True)
    label = models.CharField(max_length=60)
    icon = models.CharField(max_length=60, blank=True)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    objects = SubjectManager()

    class Meta:
        ordering = ["order", "label"]
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)[:40]
        super().save(*args, **kwargs)


# ───────────────────────────── Course ─────────────────────────────

class Course(TimeStampedModel):
    """
    A training course in the catalogue. Mirrors `courses` in
    src/data/courses.js.
    """
    class Level(models.TextChoices):
        BEGINNER     = "beginner",     "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED     = "advanced",     "Advanced"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True, db_index=True)

    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=1000)
    description = models.TextField(blank=True)

    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="courses",
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="authored_courses",
        limit_choices_to={"role__in": ["trainer", "researcher", "admin"]},
    )

    level = models.CharField(max_length=12, choices=Level.choices, db_index=True)
    hours = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(80)],
    )
    rating = models.DecimalField(
        max_digits=3, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    review_count = models.PositiveIntegerField(default=0)

    badge_enabled = models.BooleanField(default=True)
    popular = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Media
    image_url = models.ImageField(upload_to="courses/images/", blank=True, null=True)
    alt_text = models.CharField(max_length=180, blank=True)

    # Source data
    updated_source_date = models.DateField(null=True, blank=True)

    objects = CourseManager()

    class Meta:
        ordering = ["-popular", "-rating", "title"]
        indexes = [
            models.Index(fields=["subject", "is_published"]),
            models.Index(fields=["level", "is_published"]),
            models.Index(fields=["popular", "is_published"]),
            models.Index(fields=["is_published", "-rating"]),
        ]
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:80]
        if self.is_published and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    # ── Convenience ──────────────────────────────────────────────
    @property
    def subject_label(self) -> str:
        return self.subject.label

    @property
    def level_label(self) -> str:
        return self.get_level_display()

    # @property
    # def lesson_count(self) -> int:
    #     return self.lessons.count()
    
    @property
    def lesson_count(self) -> int:
        """
        Total lessons across every module in this course.

        Lessons are attached to Module, not Course, so we sum through
        the modules relation. Uses the prefetched cache when the queryset
        called `.prefetch_related("modules__lessons")`, otherwise falls
        back to a single aggregate query.
        """
        from django.db.models import Count

        # Fast path: modules are already prefetched on this instance
        try:
            modules = list(self.modules.all())
            if modules and all(
                getattr(m, "_prefetched_objects_cache", {}).get("lessons") is not None
                for m in modules
            ):
                return sum(len(list(m.lessons.all())) for m in modules)
        except Exception:
            pass

        # Fallback: aggregate at the DB level
        return (
            Lesson.objects
            .filter(module__course=self)
            .aggregate(n=Count("id"))["n"]
            or 0
        )



    @property
    def module_count(self) -> int:
        return self.modules.count()


# ───────────────────────────── Module ─────────────────────────────

class Module(TimeStampedModel):
    """
    A logical grouping of lessons inside a course.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="modules",
    )
    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=300, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = [("course", "order")]
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(order__lt=MAX_MODULES_PER_COURSE),
                name="module_order_in_range",
            ),
        ]

    def __str__(self):
        return f"{self.course.title} — {self.title}"

    @property
    def total_minutes(self) -> int:
        return sum(l.minutes for l in self.lessons.all())


# ───────────────────────────── Lesson ─────────────────────────────

class Lesson(TimeStampedModel):
    """
    A single lesson inside a module. Mirrors the `lessons` shape in
    src/data/courses.js: type, body, notes, streamUrl, resources.
    """
    class Type(models.TextChoices):
        VIDEO    = "video",    "Video"
        READING  = "reading",  "Reading"
        RESOURCE = "resource", "Resource"
        QUIZ     = "quiz",     "Quiz"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="lessons",
    )

    # Stable slug for lesson-level routing: /courses/:slug/lessons/:lessonId
    # We use the row's short integer for the URL, generated at save time.
    slug = models.SlugField(max_length=80, db_index=True)

    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    type = models.CharField(max_length=12, choices=Type.choices, default=Type.READING)
    minutes = models.PositiveSmallIntegerField(
        default=DEFAULT_LESSON_MINUTES, validators=[validate_positive_minutes],
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_preview = models.BooleanField(default=False)

    # Media — one or the other depending on type
    stream_url = models.URLField(
        blank=True, validators=[validate_lesson_stream_url],
        help_text="HLS (.m3u8) or DASH (.mpd) manifest URL",
    )
    poster_url = models.URLField(blank=True)

    # Resource (for type=resource)
    resource_file = models.FileField(upload_to="pdfs/lessons/", blank=True)
    resource_label = models.CharField(max_length=180, blank=True)

    # Bullet points shown under "Key takeaways"
    notes = models.JSONField(default=list, blank=True)

    objects = LessonManager()

    class Meta:
        ordering = ["order"]
        unique_together = [("module", "order")]
        indexes = [
            models.Index(fields=["module", "order"]),
            models.Index(fields=["type"]),
        ]
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(minutes__gte=1) & models.Q(minutes__lte=240),
                name="lesson_minutes_in_range",
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate a per-module slug like m1l2
        if not self.slug:
            module_index = self.module.order or 1
            self.slug = f"m{module_index}l{self.order or 1}"
        super().save(*args, **kwargs)

    @property
    def course(self) -> Course:
        return self.module.course


# ───────────────────────────── Resource ─────────────────────────────

class Resource(TimeStampedModel):
    """
    Attached to a lesson — a PDF, an external link, or a KALRO digital
    tool like KAMIS, KALRO Selector, KAOP.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="resources",
    )

    kind = models.CharField(max_length=8, choices=[(k, k) for k in RESOURCE_KINDS])
    title = models.CharField(max_length=180)
    publisher = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    file = models.FileField(upload_to="pdfs/resources/", blank=True)

    # Presentation
    size_label = models.CharField(max_length=40, blank=True, help_text="e.g. 'PDF · 4.2 MB'")
    category = models.CharField(max_length=40, blank=True, help_text="e.g. 'Market', 'Advisory'")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        indexes = [models.Index(fields=["lesson", "order"])]
        verbose_name = "Resource"
        verbose_name_plural = "Resources"

    def __str__(self):
        return f"{self.get_kind_display()} — {self.title}"
    

class Pathway(TimeStampedModel):
    """
    A curated set of courses that build one complete skill. Finish them
    all to earn a Pathway badge.

    Pathways are a presentation layer over `Course` — they don't own
    lessons themselves, they just group them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True, db_index=True)

    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)

    icon = models.CharField(max_length=60, blank=True)

    # Courses in this pathway, in display order.
    courses = models.ManyToManyField(
        Course,
        through="PathwayCourse",
        related_name="pathways",
        blank=True,
    )

    # The badge awarded on completion
    badge_label = models.CharField(max_length=120, blank=True)
    badge_variant = models.CharField(
        max_length=20, default="pathway",
        help_text="Colour variant used by the frontend Rosette.",
    )

    # Presentation
    cta_variant = models.CharField(
        max_length=10, default="ghost",
        choices=[("primary", "Primary"), ("ghost", "Ghost")],
    )

    is_published = models.BooleanField(default=True, db_index=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Pathway"
        verbose_name_plural = "Pathways"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)[:80]
        super().save(*args, **kwargs)

    # ── Computed stats ───────────────────────────────────────
    @property
    def course_count(self) -> int:
        return self.courses.count()

    @property
    def total_minutes(self) -> int:
        return sum(c.hours * 60 for c in self.courses.all())

    @property
    def total_hours(self) -> int:
        return max(1, round(self.total_minutes / 60))


class PathwayCourse(models.Model):
    """
    Explicit through-model so the order of courses within a pathway is
    stable and editable.
    """
    pathway = models.ForeignKey(
        Pathway, on_delete=models.CASCADE, related_name="pathway_courses"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="pathway_links"
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = [("pathway", "course")]