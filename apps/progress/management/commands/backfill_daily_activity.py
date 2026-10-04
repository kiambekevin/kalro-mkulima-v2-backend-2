# apps/progress/management/commands/backfill_daily_activity.py
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.progress.models import LessonCompletion
from apps.progress.selectors import recompute_daily_activity


class Command(BaseCommand):
    help = "Recompute DailyActivity for the last N days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--user", help="Limit to a single user email.")

    def handle(self, *args, **options):
        days = options["days"]
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)

        users_qs = User.objects.all()
        if options["user"]:
            users_qs = users_qs.filter(email=options["user"])

        active_ids = set(
            LessonCompletion.objects
            .filter(completed_at__date__gte=start)
            .values_list("user_id", flat=True)
            .distinct()
        )
        users_qs = users_qs.filter(id__in=active_ids)

        total = 0
        for user in users_qs.iterator():
            for i in range(days):
                recompute_daily_activity(user, target_date=start + timedelta(days=i))
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Recomputed activity for {total} user(s)."))