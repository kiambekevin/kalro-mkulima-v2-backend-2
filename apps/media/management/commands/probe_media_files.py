# apps/media/management/commands/probe_media_files.py
"""
Probe video files with ffprobe to fill duration, width, height.
Requires `ffprobe` on the PATH (install ffmpeg).
"""
import json
import shutil
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.media.models import MediaAsset


class Command(BaseCommand):
    help = "Probe local video files to fill duration/width/height metadata."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        if shutil.which("ffprobe") is None:
            self.stderr.write("ffprobe not found on PATH. Install ffmpeg first.")
            return

        qs = MediaAsset.objects.videos().filter(duration_seconds__isnull=True)
        if options["limit"]:
            qs = qs[: options["limit"]]

        updated = 0
        for asset in qs:
            if not asset.file:
                continue
            path = asset.file.path
            if not Path(path).exists():
                continue
            try:
                probe = subprocess.run(
                    [
                        "ffprobe", "-v", "error",
                        "-select_streams", "v:0",
                        "-show_entries", "stream=width,height:format=duration",
                        "-of", "json",
                        path,
                    ],
                    capture_output=True, text=True, check=True,
                )
                data = json.loads(probe.stdout or "{}")
                stream = (data.get("streams") or [{}])[0]
                fmt = data.get("format") or {}

                asset.width = stream.get("width") or asset.width
                asset.height = stream.get("height") or asset.height
                duration = fmt.get("duration")
                if duration:
                    asset.duration_seconds = int(float(duration))
                asset.save(update_fields=["width", "height", "duration_seconds", "updated_at"])
                updated += 1
            except subprocess.CalledProcessError as exc:
                self.stderr.write(f"{asset.slug}: ffprobe failed — {exc.stderr}")

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} asset(s)."))