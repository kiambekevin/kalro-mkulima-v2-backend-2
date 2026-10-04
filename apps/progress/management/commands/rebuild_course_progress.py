# apps/progress/management/commands/rebuild_course_progress.py
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.courses.models import Course
from apps.progress.services import rebuild_course_progress


class Command(BaseCommand):
    help = "Rebuild CourseProgress rows from LessonCompletion."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Email or phone of a single user.")
        parser.add_argument("--course", help="Slug of a single course.")
        parser.add_argument("--all", action="store_true", help="Rebuild for every user × course with completions.")

    def handle(self, *args, **options):
        if options["user"]:
            user = User.objects.filter(email=options["user"]).first() \
                or User.objects.filter(phone=options["user"]).first()
            if not user:
                self.stderr.write("User not found.")
                return
            course = None
            if options["course"]:
                course = Course.objects.filter(slug=options["course"]).first()
            if course:
                rebuild_course_progress(user, course)
                self.stdout.write(self.style.SUCCESS("Rebuilt 1 row."))
            else:
                count = 0
                from apps.progress.models import LessonCompletion
                for cid in LessonCompletion.objects.filter(user=user).values_list("course_id", flat=True).distinct():
                    c = Course.objects.filter(id=cid).first()
                    if c:
                        rebuild_course_progress(user, c)
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Rebuilt {count} row(s)."))
            return

        if options["all"]:
            from apps.progress.models import LessonCompletion
            pairs = (
                LessonCompletion.objects
                .values_list("user_id", "course_id")
                .distinct()
            )
            count = 0
            for user_id, course_id in pairs.iterator():
                user = User.objects.filter(id=user_id).first()
                course = Course.objects.filter(id=course_id).first()
                if user and course:
                    rebuild_course_progress(user, course)
                    count += 1
            self.stdout.write(self.style.SUCCESS(f"Rebuilt {count} row(s)."))
            return

        self.stderr.write("Provide --user, or --all.")