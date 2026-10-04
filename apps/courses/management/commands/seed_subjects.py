# apps/courses/management/commands/seed_subjects.py
from django.core.management.base import BaseCommand

from apps.courses.models import Subject

SUBJECTS = [
    ("crops",        "Crops",              "fa-solid fa-wheat-awn",        1),
    ("livestock",    "Livestock",          "fa-solid fa-cow",              2),
    ("natural",      "Natural Resources",  "fa-solid fa-tree",             3),
    ("water",        "Water & Irrigation", "fa-solid fa-droplet",          4),
    ("processing",   "Agro-Processing",    "fa-solid fa-jar",              5),
    ("climate",      "Climate-Smart",      "fa-solid fa-cloud-sun-rain",   6),
    ("agribusiness", "Agribusiness",       "fa-solid fa-chart-line",       7),
]


class Command(BaseCommand):
    help = "Create or update the seven standard subjects."

    def handle(self, *args, **options):
        created = updated = 0
        for slug, label, icon, order in SUBJECTS:
            obj, is_new = Subject.objects.update_or_create(
                slug=slug,
                defaults={"label": label, "icon": icon, "order": order},
            )
            created += 1 if is_new else 0
            updated += 0 if is_new else 1
        self.stdout.write(self.style.SUCCESS(
            f"Subjects — {created} created, {updated} updated."
        ))