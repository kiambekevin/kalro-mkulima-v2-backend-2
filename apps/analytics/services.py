# apps/analytics/services.py
"""
Business logic for recording visits. Called by the API view, not the
model, so the model stays a plain data structure.
"""
import hashlib
import logging

from django.utils import timezone

from apps.courses.models import Course, Lesson
from .models import VisitEvent

logger = logging.getLogger(__name__)


def record_course_visit(*, user, session_id, course_slug, request=None):
    course = Course.objects.filter(slug=course_slug).first()
    if not course:
        return None
    return _record(
        user=user,
        session_id=session_id,
        resource_type=VisitEvent.ResourceType.COURSE,
        course=course,
        request=request,
    )


def record_lesson_visit(*, user, session_id, course_slug, lesson_identifier, request=None):
    lesson = (
        Lesson.objects
        .filter(module__course__slug=course_slug)
        .filter(slug=lesson_identifier)
        .select_related("module", "module__course")
        .first()
    )
    if not lesson:
        return None
    return _record(
        user=user,
        session_id=session_id,
        resource_type=VisitEvent.ResourceType.LESSON,
        course=lesson.module.course,
        lesson=lesson,
        request=request,
    )


def _record(*, user, session_id, resource_type, course=None, lesson=None, request=None):
    """
    Insert one visit row. The county is denormalised from the user's
    profile at the moment of the visit — later moves don't rewrite
    history.
    """
    county = None
    if user and getattr(user, "profile", None):
        county = getattr(user.profile, "county", None)

    ip = ua = None
    if request is not None:
        ip = _client_ip(request)
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:300]

    # Anonymous sessions use a hashed session id
    if not session_id:
        session_id = _make_session_id(user, ip, ua)

    event = VisitEvent.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        session_id=session_id,
        resource_type=resource_type,
        course=course,
        lesson=lesson,
        county=county,
        ip_address=ip,
        user_agent=ua,
    )
    logger.debug("Recorded %s visit for %s", resource_type, course.slug if course else "—")
    return event


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _make_session_id(user, ip, ua):
    seed = f"{getattr(user, 'id', '')}|{ip}|{ua}|{timezone.now().date()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]

def _infer_county_from_ip(ip):
    """
    Very rough mapping. In production, plug in MaxMind GeoIP2 or a
    Kenyan ISP lookup table. For now, no-op so nothing breaks.
    """
    return None