# apps/accounts/managers.py
from django.contrib.auth.models import BaseUserManager
from django.db import transaction


class UserManager(BaseUserManager):
    """
    Custom user manager keyed on email. Phone is required but not the login
    identifier — the API accepts either email or phone in the login payload.
    """
    use_in_migrations = True

    def _create_user(self, email, phone, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not phone:
            raise ValueError("A phone number is required.")

        email = self.normalize_email(email).lower()

        with transaction.atomic():
            user = self.model(email=email, phone=phone, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
        return user

    def create_user(self, email, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "farmer")
        return self._create_user(email, phone, password, **extra_fields)

    def create_superuser(self, email, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, phone, password, **extra_fields)

    def get_by_natural_key(self, username):
        """
        Allow login by either email or phone. SimpleJWT calls this with the
        value the user submitted as `email` in the login payload.
        """
        return self.get(email__iexact=username) if "@" in username \
            else self.get(phone=username)