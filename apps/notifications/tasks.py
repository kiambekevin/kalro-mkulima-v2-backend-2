# apps/notifications/tasks.py
from celery import shared_task
from .providers import africastalking as at

@shared_task(bind=True, max_retries=3)
def send_sms(self, phone, message):
    try:
        at.send(phone, message)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)