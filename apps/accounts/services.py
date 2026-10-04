# apps/accounts/services.py
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


def issue_tokens_for_user(user: User, remember: bool = False):
    """
    Returns access + refresh tokens. `remember` extends the refresh token
    lifetime (opt-in on the login form).
    """
    refresh = RefreshToken.for_user(user)

    if remember:
        from datetime import timedelta
        refresh.set_exp(lifetime=timedelta(days=90))

    # Embed a few useful claims
    refresh["role"] = user.role
    refresh["name"] = user.display_name

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def revoke_refresh_token(raw_refresh: str) -> bool:
    """Blacklist a refresh token (logout). Returns True on success."""
    try:
        RefreshToken(raw_refresh).blacklist()
        return True
    except Exception:
        return False


@transaction.atomic
def register_user(*, cleaned_data: dict) -> User:
    """
    Thin wrapper around RegisterSerializer.create so views stay clean
    and other services (management commands, seeds) can call it.
    """
    from .serializers import RegisterSerializer
    serializer = RegisterSerializer(data=cleaned_data)
    serializer.is_valid(raise_exception=True)
    return serializer.save()