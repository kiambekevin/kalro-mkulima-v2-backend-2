# apps/dashboard/management/commands/warm_dashboard_cache.py
"""
Pre-compute learner and county dashboards. Run nightly or right before
peak hours so the first request of the day is fast.
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.counties.models import County
from apps.dashboard.services import (
    build_county_dashboard,
    build_learner_dashboard,
)


class Command(BaseCommand):
    help = "Precompute dashboard payloads and store them in cache."

    def add_arguments(self, parser):
        parser.add_argument(
            "--active-hours", type=int, default=24 * 7,
            help="Only warm dashboards for users active in the last N hours.",
        )
        parser.add_argument(
            "--skip-users", action="store_true",
        )
        parser.add_argument(
            "--skip-counties", action="store_true",
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from datetime import timedelta

        if not options["skip_users"]:
            cutoff = timezone.now() - timedelta(hours=options["active_hours"])
            users = User.objects.filter(
                is_active=True, last_seen_at__gte=cutoff,
            ).select_related("profile", "profile__county")
            count = 0
            for user in users.iterator():
                build_learner_dashboard(user)
                count += 1
            self.stdout.write(self.style.SUCCESS(f"Warmed {count} learner dashboard(s)."))

        if not options["skip_counties"]:
            count = 0
            for county in County.objects.all():
                build_county_dashboard(county)
                count += 1
            self.stdout.write(self.style.SUCCESS(f"Warmed {count} county dashboard(s)."))