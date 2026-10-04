# apps/courses/management/commands/seed_courses.py
"""
Load courses from a JSON file matching the shape of
src/data/courses.js. The same file can be exported from the frontend
or authored by content editors.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.courses.services import import_course_from_dict


class Command(BaseCommand):
    help = "Import courses from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "path", type=str,
            help="Path to a JSON file: either a single course object or a list.",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else [raw]

        if options["dry_run"]:
            self.stdout.write(f"Would import {len(items)} course(s).")
            return

        for payload in items:
            course = import_course_from_dict(payload)
            self.stdout.write(self.style.SUCCESS(
                f"Imported {course.slug} ({course.lessons.count()} lessons)"
            ))