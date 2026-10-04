# apps/courses/filters.py
"""
Filter set for the course catalogue. Mirrors the frontend's
`useCourses` hook: search, subject, level, duration, pathway, popular.

Every filter is designed to tolerate empty values, so the frontend can
send all query params on every request without branching.
"""
import django_filters
from django.db.models import Q

from .models import Course


DURATION_BUCKETS = {
    "short":  (0, 4),      # under 4 hours
    "medium": (4, 8),      # 4 – 8 hours
    "long":   (8, 999),    # over 8 hours
}

SORT_MAP = {
    "popular":   ("-popular", "-rating", "title"),
    "newest":    ("-updated_source_date", "-created_at"),
    "rating":    ("-rating", "-review_count"),
    "az":        ("title",),
}


class CourseFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="Search")

    # Accept comma-separated lists: ?subject=crops,livestock
    subject = django_filters.BaseInFilter(
        field_name="subject__slug", lookup_expr="in",
    )
    level = django_filters.BaseInFilter(
        field_name="level", lookup_expr="in",
    )
    duration = django_filters.CharFilter(
        method="filter_duration", label="Duration",
    )
    pathway = django_filters.CharFilter(
        method="filter_pathway", label="Pathway",
    )
    popular = django_filters.BooleanFilter(field_name="popular")

    class Meta:
        model = Course
        fields = ["subject", "level", "duration", "popular", "pathway"]

    # ── Search ─────────────────────────────────────────────────

    def filter_search(self, qs, name, value):
        """
        Match `q` against title, summary, description, and subject
        label. Case-insensitive, trimmed, safe against blank input.
        """
        value = (value or "").strip()
        if not value:
            return qs

        return qs.filter(
            Q(title__icontains=value)
            | Q(summary__icontains=value)
            | Q(description__icontains=value)
            | Q(subject__label__icontains=value)
        )

    # ── Duration ───────────────────────────────────────────────

    def filter_duration(self, qs, name, value):
        """
        Bucket by hours: short / medium / long.
        """
        bucket = DURATION_BUCKETS.get((value or "").strip().lower())
        if not bucket:
            return qs
        lo, hi = bucket
        return qs.filter(hours__gt=lo, hours__lte=hi)

    # ── Pathway ────────────────────────────────────────────────

    def filter_pathway(self, qs, name, value):
        """
        Restrict to the courses that belong to the given pathway slug.
        Assumes the `Pathway` model with a `pathway_courses` through
        table (see apps/courses/models.py).
        """
        value = (value or "").strip()
        if not value:
            return qs
        return qs.filter(pathways__slug=value).distinct()
    
