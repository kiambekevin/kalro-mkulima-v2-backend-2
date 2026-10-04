# apps/accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ProfileUpdateView,
    PasswordChangeView,
    EmailAvailabilityView,
    PhoneAvailabilityView,
)

app_name = "accounts"

urlpatterns = [
    # Auth
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # JWT primitives (kept for compatibility with mobile / low-level clients)
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # Current user
    path("me/", MeView.as_view(), name="me"),
    path("me/profile/", ProfileUpdateView.as_view(), name="me-profile"),
    path("me/password/", PasswordChangeView.as_view(), name="me-password"),

    # Availability checks used by the register form
    path("check/email/", EmailAvailabilityView.as_view(), name="check-email"),
    path("check/phone/", PhoneAvailabilityView.as_view(), name="check-phone"),
]