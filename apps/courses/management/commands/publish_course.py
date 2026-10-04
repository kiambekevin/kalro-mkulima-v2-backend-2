# apps/courses/management/commands/publish_course.py
from django.core.management.base import BaseCommand, CommandError

from apps.courses.models import Course
from apps.courses.services import publish_course, PublishError


class Command(BaseCommand):
    help = "Publish a course by slug."

    def add_arguments(self, parser):
        parser.add_argument("slug", type=str)

    def handle(self, *args, **options):
        try:
            course = Course.objects.get(slug=options["slug"])
        except Course.DoesNotExist:
            raise CommandError(f"No course with slug '{options['slug']}'.")

        try:
            publish_course(course)
        except PublishError as exc:
            raise CommandError(str(exc))

        self.stdout.write(self.style.SUCCESS(f"Published {course.slug}."))