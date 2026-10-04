# apps/badges/management/commands/regenerate_badge_pngs.py
from django.core.management.base import BaseCommand

from apps.badges.models import Badge
from apps.badges import tasks


class Command(BaseCommand):
    help = "Re-render PNGs for every badge (or a filtered subset)."

    def add_arguments(self, parser):
        parser.add_argument("--subject", help="Only badges in this subject slug.")
        parser.add_argument("--limit", type=int, default=0, help="Stop after N badges.")
        parser.add_argument("--sync", action="store_true",
                            help="Render inline instead of queuing a Celery task.")

    def handle(self, *args, **options):
        qs = Badge.objects.select_related("course", "course__subject").issued()

        if options["subject"]:
            qs = qs.filter(course__subject__slug=options["subject"])
        if options["limit"]:
            qs = qs[: options["limit"]]

        count = 0
        for badge in qs:
            if options["sync"]:
                from apps.badges.renderers import save_badge_png
                save_badge_png(badge, overwrite=True)
            else:
                tasks.render_badge_png_task.delay(badge.id, overwrite=True)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Queued/rendered {count} badge PNG(s)."))