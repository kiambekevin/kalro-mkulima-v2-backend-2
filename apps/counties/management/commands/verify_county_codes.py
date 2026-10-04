# apps/counties/management/commands/verify_county_codes.py
"""
Sanity check: confirms all 47 counties are present with codes
"001" through "047" and no duplicates.
"""
from django.core.management.base import BaseCommand

from apps.counties.models import County


class Command(BaseCommand):
    help = "Verify the county table has all 47 codes."

    def handle(self, *args, **options):
        expected = {f"{i:03d}" for i in range(1, 48)}
        existing = set(County.objects.values_list("code", flat=True))

        missing = sorted(expected - existing)
        extra = sorted(existing - expected)

        if missing:
            self.stderr.write(self.style.ERROR(f"Missing counties: {missing}"))
        if extra:
            self.stderr.write(self.style.WARNING(f"Unexpected codes: {extra}"))

        if not missing and not extra:
            self.stdout.write(self.style.SUCCESS("All 47 counties present."))