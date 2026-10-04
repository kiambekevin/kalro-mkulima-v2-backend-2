# apps/fielddays/management/commands/send_reminders.py
from django.core.management.base import BaseCommand

from apps.fielddays.tasks import send_upcoming_reminders


class Command(BaseCommand):
    help = "Send upcoming field-day reminders synchronously (dev)."

    def handle(self, *args, **options):
        count = send_upcoming_reminders()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} reminder(s)."))