# apps/accounts/management/commands/create_default_superuser.py
import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_* env vars if none exists."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        phone = os.environ.get("DJANGO_SUPERUSER_PHONE")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([email, phone, password]):
            self.stdout.write(self.style.WARNING(
                "DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PHONE and "
                "DJANGO_SUPERUSER_PASSWORD must all be set. Skipping."
            ))
            return

        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(self.style.NOTICE(f"Superuser {email} already exists."))
            return

        User.objects.create_superuser(email=email, phone=phone, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser {email}."))