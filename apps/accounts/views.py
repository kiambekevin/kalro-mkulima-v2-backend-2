# apps/accounts/views.py
from django.db import transaction
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsSelfOrAdmin
from .selectors import get_user_with_profile
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    MeSerializer,
    UserUpdateSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    PasswordChangeSerializer,
)
from .services import issue_tokens_for_user, revoke_refresh_token


# ─────────────────────────── Register ───────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = issue_tokens_for_user(user)
        return Response(
            {
                "user": MeSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────── Login ───────────────────────────

class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        remember = serializer.validated_data.get("remember", False)

        # Update last seen on explicit login too
        user.touch_last_seen()

        tokens = issue_tokens_for_user(user, remember=remember)
        return Response(
            {
                "user": MeSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


# ─────────────────────────── Logout ───────────────────────────

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "A refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        revoke_refresh_token(refresh)
        return Response(status=status.HTTP_205_RESET_CONTENT)


# ─────────────────────────── Me (read + update) ───────────────────────────

class MeView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsSelfOrAdmin]

    def get_object(self):
        return get_user_with_profile(self.request.user.id)

    def get_serializer_class(self):
        return MeSerializer if self.request.method == "GET" else UserUpdateSerializer

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MeSerializer(user).data)


# ─────────────────────────── Profile update ───────────────────────────

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile = request.user.profile
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(profile).data)


# ─────────────────────────── Password change ───────────────────────────

class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated successfully."})


# ─────────────────────────── Availability checks ───────────────────────────

class EmailAvailabilityView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from .selectors import user_exists_by_email
        email = request.query_params.get("email", "").strip()
        return Response({"available": bool(email) and not user_exists_by_email(email)})


class PhoneAvailabilityView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from .selectors import user_exists_by_phone
        phone = request.query_params.get("phone", "").strip()
        return Response({"available": bool(phone) and not user_exists_by_phone(phone)})