# apps/progress/filters.py
import django_filters

from .models import CourseProgress, LessonCompletion


class CourseProgressFilter(django_filters.FilterSet):
    course = django_filters.CharFilter(field_name="course__slug")
    subject = django_filters.CharFilter(field_name="course__subject__slug")
    status = django_filters.CharFilter(method="filter_status")
    min_percent = django_filters.NumberFilter(field_name="percent", lookup_expr="gte")
    max_percent = django_filters.NumberFilter(field_name="percent", lookup_expr="lte")

    class Meta:
        model = CourseProgress
        fields = ["course", "subject"]

    def filter_status(self, qs, name, value):
        if value == "in_progress":
            return qs.filter(percent__gt=0, percent__lt=100)
        if value == "completed":
            return qs.filter(percent__gte=100)
        if value == "not_started":
            return qs.filter(percent=0)
        return qs


class LessonCompletionFilter(django_filters.FilterSet):
    course = django_filters.CharFilter(field_name="course__slug")
    lesson = django_filters.UUIDFilter(field_name="lesson__id")
    from_date = django_filters.DateFilter(field_name="completed_at", lookup_expr="date__gte")
    to_date = django_filters.DateFilter(field_name="completed_at", lookup_expr="date__lte")

    class Meta:
        model = LessonCompletion
        fields = ["course", "lesson"]