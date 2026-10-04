# apps/fielddays/management/commands/close_past_events.py
from django.core.management.base import BaseCommand

from apps.fielddays.services import close_past_events


class Command(BaseCommand):
    help = "Mark past field days as COMPLETED and no-show confirmed bookings."

    def handle(self, *args, **options):
        count = close_past_events()
        self.stdout.write(self.style.SUCCESS(f"Closed {count} past field day(s)."))