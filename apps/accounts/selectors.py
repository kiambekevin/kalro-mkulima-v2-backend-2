# apps/accounts/selectors.py
from django.db.models import Prefetch

from .models import User, Profile


def get_user_with_profile(user_id):
    """Optimised single-user fetch for /auth/me/ and dashboards."""
    return (
        User.objects
        .select_related("profile", "profile__county")
        .prefetch_related(
            Prefetch("profile__value_chains", to_attr="_value_chains"),
        )
        .get(pk=user_id)
    )


def user_exists_by_email(email: str) -> bool:
    return User.objects.filter(email__iexact=email).exists()


def user_exists_by_phone(phone: str) -> bool:
    return User.objects.filter(phone=phone).exists()