# apps/badges/management/commands/seed_badge_templates.py
from django.core.management.base import BaseCommand

from apps.courses.models import Subject
from apps.badges.services import ensure_template_for_subject

# Sensible defaults per subject slug — mirrors src/data/badges.js on the frontend
THEMES = {
    "livestock":    {"tint_hex": "#23804A", "accent_hex": "#F0B429", "icon": "fa-solid fa-cow"},
    "crops":        {"tint_hex": "#1B6639", "accent_hex": "#F0B429", "icon": "fa-solid fa-wheat-awn"},
    "natural":      {"tint_hex": "#123B26", "accent_hex": "#F0B429", "icon": "fa-solid fa-tree"},
    "water":        {"tint_hex": "#1E6FA8", "accent_hex": "#F0B429", "icon": "fa-solid fa-droplet"},
    "processing":   {"tint_hex": "#8B5A36", "accent_hex": "#F0B429", "icon": "fa-solid fa-jar"},
    "climate":      {"tint_hex": "#2F9A5A", "accent_hex": "#F0B429", "icon": "fa-solid fa-cloud-sun-rain"},
    "agribusiness": {"tint_hex": "#B7801A", "accent_hex": "#123B26", "icon": "fa-solid fa-chart-line"},
}


class Command(BaseCommand):
    help = "Create a BadgeTemplate for every Subject using the standard palette."

    def handle(self, *args, **options):
        created = updated = 0

        for subject in Subject.objects.all():
            theme = THEMES.get(subject.slug, {})
            template = ensure_template_for_subject(subject)

            changed = False
            for field, value in theme.items():
                if value and getattr(template, field) != value:
                    setattr(template, field, value)
                    changed = True

            if changed:
                template.save()
                updated += 1
            else:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Badge templates — {created} present, {updated} updated."
        ))