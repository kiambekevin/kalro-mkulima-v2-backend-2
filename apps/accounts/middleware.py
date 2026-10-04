# apps/accounts/middleware.py
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class LastSeenMiddleware(MiddlewareMixin):
    """
    Updates `User.last_seen_at` on each authenticated request, throttled
    to once every 5 minutes to avoid hammering the DB.
    """
    THROTTLE_SECONDS = 300

    def process_request(self, request):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return
        now = timezone.now()
        last = user.last_seen_at
        if last is None or (now - last).total_seconds() > self.THROTTLE_SECONDS:
            user.last_seen_at = now
            user.save(update_fields=["last_seen_at"])