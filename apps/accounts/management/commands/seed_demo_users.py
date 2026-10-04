# apps/accounts/management/commands/seed_demo_users.py
from django.core.management.base import BaseCommand

from apps.accounts.models import User


DEMO_USERS = [
    ("farmer@demo.kalro.org",     "+254700000001", "farmer",      "Wanjiku", "Muthoni"),
    ("trainer@demo.kalro.org",    "+254700000002", "trainer",     "James",   "Ochieng"),
    ("extension@demo.kalro.org",  "+254700000003", "extension",   "Amina",   "Khalid"),
    ("county@demo.kalro.org",     "+254700000004", "county",      "Peter",   "Kamau"),
    ("researcher@demo.kalro.org", "+254700000005", "researcher",  "Margaret","Otieno"),
]


class Command(BaseCommand):
    help = "Create demo users for local development."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo-pass-1234")

    def handle(self, *args, **options):
        password = options["password"]
        for email, phone, role, first, last in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "phone": phone,
                    "role": role,
                    "first_name": first,
                    "last_name": last,
                },
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created {email} ({role})"))
            else:
                self.stdout.write(self.style.NOTICE(f"Exists  {email}"))
        self.stdout.write(self.style.SUCCESS(f"All demo users use password: {password}"))