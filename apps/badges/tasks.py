# apps/badges/tasks.py
"""
Background tasks for badge rendering and notifications.

Kept thin — heavy lifting lives in `renderers.py` and `services.py`
so these tasks are easy to test and reason about.
"""
import logging

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .models import Badge
from .renderers import save_badge_png, render_badge_png_bytes

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def render_badge_png_task(self, badge_id, overwrite=False):
    """Render the badge PNG and attach it to the Badge row."""
    try:
        badge = Badge.objects.select_related(
            "course", "course__subject", "user"
        ).get(id=badge_id)
    except Badge.DoesNotExist:
        logger.warning("Badge %s not found — skipping PNG render.", badge_id)
        return

    try:
        name = save_badge_png(badge, overwrite=overwrite)
        logger.info("Rendered badge PNG %s → %s", badge.badge_id, name)
        return name
    except Exception as exc:  # noqa: BLE001
        logger.exception("PNG render failed for badge %s", badge.badge_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_badge_email_task(self, badge_id):
    """Email the learner with their badge PNG attached."""
    try:
        badge = Badge.objects.select_related(
            "course", "course__subject", "user"
        ).get(id=badge_id)
    except Badge.DoesNotExist:
        return

    user = badge.user
    if not user.email:
        return

    subject = f"Your KALRO badge — {badge.snapshot.get('course_title') or badge.course.title}"
    verify_url = (
        f"{getattr(settings, 'KALRO_BADGE_VERIFY_BASE_URL', 'https://mkulima.kalro.org/badges/verify').rstrip('/')}"
        f"/{badge.badge_id}"
    )

    text_body = (
        f"Karibu {user.first_name or user.email},\n\n"
        f"Congratulations — you've earned a verified KALRO digital badge for:\n"
        f"  {badge.snapshot.get('course_title') or badge.course.title}\n\n"
        f"Badge ID: {badge.badge_id}\n"
        f"Verify online: {verify_url}\n\n"
        f"You can also share this badge with buyers, cooperatives and county programs.\n\n"
        f"— KALRO Mkulima team"
    )

    html_body = f"""
    <div style="font-family:system-ui,-apple-system,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#123B26;margin-bottom:4px">Congratulations, {user.first_name or user.email}!</h2>
      <p style="color:#55655B">You've earned a verified KALRO digital badge for:</p>
      <h3 style="color:#123B26;margin-top:8px">{badge.snapshot.get('course_title') or badge.course.title}</h3>
      <p><strong>Badge ID:</strong> <code>{badge.badge_id}</code></p>
      <p><a href="{verify_url}" style="color:#1B6639">Verify online →</a></p>
      <p style="color:#55655B;font-size:13px;margin-top:24px">— KALRO Mkulima team</p>
    </div>
    """

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")

    # Attach the PNG (render on demand if the async render hasn't finished)
    try:
        if badge.png_file:
            badge.png_file.open("rb")
            msg.attach(f"{badge.badge_id}.png", badge.png_file.read(), "image/png")
        else:
            msg.attach(f"{badge.badge_id}.png", render_badge_png_bytes(badge), "image/png")
    except Exception:  # noqa: BLE001
        logger.warning("Could not attach PNG for badge %s", badge.badge_id)

    try:
        msg.send(fail_silently=False)
        logger.info("Emailed badge %s to %s", badge.badge_id, user.email)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@shared_task
def send_badge_sms_task(badge_id, phone):
    """Optional SMS notification via the notifications app."""
    from apps.notifications.services import send_sms

    try:
        badge = Badge.objects.get(id=badge_id)
    except Badge.DoesNotExist:
        return

    message = (
        f"KALRO Mkulima: You earned a badge for {badge.snapshot.get('course_title') or badge.course.title}. "
        f"ID {badge.badge_id}. View it in your wallet."
    )
    send_sms(phone, message)