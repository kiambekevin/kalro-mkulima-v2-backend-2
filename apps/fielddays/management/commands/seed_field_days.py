# apps/fielddays/management/commands/seed_field_days.py
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.counties.models import County
from apps.courses.models import Subject
from apps.fielddays.models import FieldDay

SAMPLE_EVENTS = [
    {
        "title": "Dairy feeding demonstration",
        "county": "Nakuru",
        "venue": "KALRO Naivasha Research Centre",
        "topic_slug": "livestock",
        "days_from_now": 7,
        "time": "09:00",
        "duration_hours": 4,
        "host": "Dr. Margaret Otieno",
        "spots": 40,
        "description": "Practical demonstration of home-mixed dairy rations with locally available feeds.",
    },
    {
        "title": "Climate-smart maize field day",
        "county": "Kakamega",
        "venue": "Bukura ATC demo plots",
        "topic_slug": "crops",
        "days_from_now": 14,
        "time": "08:30",
        "duration_hours": 5,
        "host": "KALRO Kakamega",
        "spots": 60,
        "description": "Showcase of drought-tolerant maize varieties and conservation tillage.",
    },
    {
        "title": "Drip irrigation installation clinic",
        "county": "Machakos",
        "venue": "KALRO Katumani",
        "topic_slug": "water",
        "days_from_now": 20,
        "time": "09:00",
        "duration_hours": 6,
        "host": "KALRO Katumani",
        "spots": 30,
        "description": "Hands-on session assembling a low-cost drip irrigation kit.",
    },
    {
        "title": "Beehive construction & colony transfer",
        "county": "Kitui",
        "venue": "Kitui Farmers Training Centre",
        "topic_slug": "livestock",
        "days_from_now": 28,
        "time": "09:00",
        "duration_hours": 4,
        "host": "KALRO Kibwezi",
        "spots": 25,
        "description": "Build a Kenya Top Bar hive and transfer a colony safely.",
    },
]


class Command(BaseCommand):
    help = "Seed sample field days for local development."

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for spec in SAMPLE_EVENTS:
            county = County.objects.filter(name__iexact=spec["county"]).first()
            topic = Subject.objects.filter(slug=spec["topic_slug"]).first()

            if not county or not topic:
                self.stdout.write(self.style.WARNING(
                    f"Skipping '{spec['title']}': missing county or topic fixture."
                ))
                skipped += 1
                continue

            # Compute a timezone-aware start
            now = timezone.localtime()
            start_date = (now + timedelta(days=spec["days_from_now"])).date()
            hh, mm = map(int, spec["time"].split(":"))
            starts_at = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time()).replace(hour=hh, minute=mm),
                timezone.get_current_timezone(),
            )
            ends_at = starts_at + timedelta(hours=spec["duration_hours"])

            _, is_new = FieldDay.objects.get_or_create(
                title=spec["title"],
                county=county,
                defaults={
                    "venue": spec["venue"],
                    "topic": topic,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "host": spec["host"],
                    "spots": spec["spots"],
                    "description": spec["description"],
                    "status": FieldDay.Status.PUBLISHED,
                },
            )
            created += 1 if is_new else 0

        self.stdout.write(self.style.SUCCESS(
            f"Field days — {created} created, {skipped} skipped."
        ))