from django.shortcuts import render

# Create your views here.
# apps/fielddays/views.py
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import FieldDayFilter, BookingFilter
from .models import FieldDay, Booking, Attendance
from .permissions import CanManageFieldDay, IsHostOrAdmin, IsBookingOwner, CanCheckIn
from .selectors import (
    upcoming_field_days,
    field_day_by_slug,
    bookings_for_field_day,
    bookings_for_user,
    booking_by_code,
    waitlist_position,
)
from .serializers import (
    FieldDaySerializer,
    FieldDayCompactSerializer,
    FieldDayWriteSerializer,
    BookingSerializer,
    AttendanceSerializer,
    CheckinSerializer,
)
from .services import (
    book_field_day,
    cancel_booking,
    check_in_booking,
    BookingError,
    CheckinError,
)


# ───────────────────────────── Field days ─────────────────────────────

class FieldDayViewSet(viewsets.ModelViewSet):
    """
    Public list/detail plus host-only authoring.
      GET    /api/v1/fielddays/                      → filterable list
      GET    /api/v1/fielddays/{slug}/               → detail
      GET    /api/v1/fielddays/upcoming/             → next 5 events
      POST   /api/v1/fielddays/{slug}/book/          → book a spot
      POST   /api/v1/fielddays/{slug}/cancel/        → cancel my booking
      GET    /api/v1/fielddays/{slug}/bookings/      → host-only list
      POST   /api/v1/fielddays/{slug}/publish/       → host-only publish
    """
    lookup_field = "slug"
    filterset_class = FieldDayFilter
    search_fields = ["title", "description", "venue"]
    ordering_fields = ["starts_at", "spots", "created_at"]

    def get_queryset(self):
        qs = FieldDay.objects.published().select_related("county", "topic")
        if self.request.user.is_authenticated and self.request.user.is_staff:
            qs = FieldDay.objects.select_related("county", "topic")
        return qs.with_attendance_counts()

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return FieldDayWriteSerializer
        return FieldDaySerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "publish"):
            return [CanManageFieldDay(), IsHostOrAdmin()]
        return [AllowAny()]

    def get_object(self):
        slug = self.kwargs["slug"]
        fd = field_day_by_slug(slug)
        if not fd:
            from django.http import Http404
            raise Http404
        self.check_object_permissions(self.request, fd)
        return fd

    # ── Custom actions ──────────────────────────────────────────

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def upcoming(self, request):
        county = None
        if request.user.is_authenticated:
            county = getattr(getattr(request.user, "profile", None), "county", None)
        data = FieldDayCompactSerializer(upcoming_field_days(county=county, limit=5), many=True).data
        return Response(data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def book(self, request, slug=None):
        fd = self.get_object()
        try:
            booking, created = book_field_day(request.user, fd)
        except BookingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        body = BookingSerializer(booking, context={"request": request}).data
        if booking.status == "waitlisted":
            body["waitlist_position"] = waitlist_position(fd, booking)
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def cancel(self, request, slug=None):
        fd = self.get_object()
        booking = Booking.objects.filter(user=request.user, field_day=fd).first()
        if not booking:
            return Response({"detail": "You have no booking for this field day."}, status=404)
        cancel_booking(booking)
        return Response({"detail": "Booking cancelled."})

    @action(detail=True, methods=["get"], permission_classes=[CanManageFieldDay, IsHostOrAdmin])
    def bookings(self, request, slug=None):
        fd = self.get_object()
        data = BookingSerializer(
            bookings_for_field_day(fd), many=True, context={"request": request},
        ).data
        return Response(data)

    @action(detail=True, methods=["post"], permission_classes=[CanManageFieldDay, IsHostOrAdmin])
    def publish(self, request, slug=None):
        fd = self.get_object()
        fd.publish()
        return Response(FieldDaySerializer(fd).data)


# ───────────────────────────── My bookings ─────────────────────────────

class MyBookingsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Authenticated user's bookings.
      GET /api/v1/fielddays/my-bookings/
    """
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = BookingFilter

    def get_queryset(self):
        return bookings_for_user(self.request.user)


# ───────────────────────────── Check-in ─────────────────────────────

class CheckinView(APIView):
    """
    POST /api/v1/fielddays/checkin/
    Body: { code, latitude, longitude, notes }
    """
    permission_classes = [IsAuthenticated, CanCheckIn]

    def post(self, request):
        serializer = CheckinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("code"):
            booking = booking_by_code(serializer.validated_data["code"])
        else:
            booking = Booking.objects.filter(id=serializer.validated_data["booking_id"]).first()

        if not booking:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            attendance = check_in_booking(
                booking=booking,
                checked_in_by=request.user,
                latitude=serializer.validated_data.get("latitude"),
                longitude=serializer.validated_data.get("longitude"),
                notes=serializer.validated_data.get("notes", ""),
            )
        except CheckinError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)


class AttendanceListView(APIView):
    """
    GET /api/v1/fielddays/{slug}/attendance/
    Host-only list of check-ins.
    """
    permission_classes = [IsAuthenticated, CanCheckIn]

    def get(self, request, slug):
        fd = get_object_or_404(FieldDay, slug=slug)
        rows = Attendance.objects.filter(booking__field_day=fd).select_related(
            "booking", "booking__user", "checked_in_by"
        )
        return Response(AttendanceSerializer(rows, many=True).data)