# apps/media/management/commands/backfill_media_durations.py
from django.core.management.base import BaseCommand

from apps.media.models import MediaAsset
from apps.media import tasks


class Command(BaseCommand):
    help = "Re-run integrity/transcode jobs for media assets."

    def add_arguments(self, parser):
        parser.add_argument("--videos", action="store_true")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        qs = MediaAsset.objects.all()
        if options["videos"] and not options["all"]:
            qs = qs.videos()

        count = 0
        for asset in qs:
            if asset.kind == MediaAsset.Kind.VIDEO and not asset.manifest_url:
                tasks.trigger_transcode.delay(asset.id)
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Queued {count} transcode job(s)."))