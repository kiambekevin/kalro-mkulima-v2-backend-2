# apps/counties/management/commands/seed_counties.py
"""
Idempotent seeding of the 47 counties. Runs even if the fixture file
only contains a subset — sub-counties and wards are optional.
"""
from pathlib import Path
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.counties.services import import_counties, import_sub_counties, import_wards


class Command(BaseCommand):
    help = "Load the 47 counties (and optional sub-counties/wards) from fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixtures-dir",
            default=None,
            help="Directory containing counties.json, sub_counties.json, wards.json",
        )

    def handle(self, *args, **options):
        base = Path(options["fixtures_dir"]) if options["fixtures_dir"] else (
            Path(settings.BASE_DIR) / "apps" / "counties" / "fixtures"
        )

        counties_path = base / "counties.json"
        if not counties_path.exists():
            raise CommandError(f"Missing fixture file: {counties_path}")

        counties_payload = json.loads(counties_path.read_text(encoding="utf-8"))
        self._load_counties(counties_payload)

        sc_path = base / "sub_counties.json"
        if sc_path.exists():
            self._load_sub_counties(json.loads(sc_path.read_text(encoding="utf-8")))

        w_path = base / "wards.json"
        if w_path.exists():
            self._load_wards(json.loads(w_path.read_text(encoding="utf-8")))

    def _load_counties(self, payload):
        flat = [
            {**item["fields"]}
            for item in payload
            if item.get("model", "").endswith("county")
        ]
        result = import_counties(flat)
        self.stdout.write(self.style.SUCCESS(
            f"Counties — created: {result['created']}, updated: {result['updated']}"
        ))

    def _load_sub_counties(self, payload):
        flat = [
            {**item["fields"], "county_code": item["fields"].get("county_code", "")}
            for item in payload
            if item.get("model", "").endswith("subcounty")
        ]
        result = import_sub_counties(flat)
        self.stdout.write(self.style.SUCCESS(
            f"Sub-counties — created: {result['created']}, updated: {result['updated']}, "
            f"skipped: {result['skipped']}"
        ))

    def _load_wards(self, payload):
        flat = [
            {**item["fields"], "county_code": item["fields"].get("county_code", "")}
            for item in payload
            if item.get("model", "").endswith("ward")
        ]
        result = import_wards(flat)
        self.stdout.write(self.style.SUCCESS(
            f"Wards — created: {result['created']}, updated: {result['updated']}, "
            f"skipped: {result['skipped']}"
        ))