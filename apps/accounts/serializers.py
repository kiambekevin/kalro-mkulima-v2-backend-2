# apps/accounts/serializers.py
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField

from .models import User, Profile
from .validators import validate_not_disallowed_email, validate_kenyan_id


# ─────────────────────────── User (read) ───────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """Safe, read-only representation used in `me/` and dashboard payloads."""
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "phone",
            "first_name", "last_name",
            "role", "preferred_language",
            "is_active", "is_verified",
            "full_name", "display_name", "initials",
            "created_at",
        ]
        read_only_fields = [
            "id", "is_active", "is_verified",
            "full_name", "display_name", "initials", "created_at",
        ]


# ─────────────────────────── Profile (read/write) ───────────────────────────

class ProfileSerializer(serializers.ModelSerializer):
    county_name = serializers.CharField(source="county.name", read_only=True)
    age = serializers.IntegerField(read_only=True)
    is_youth = serializers.BooleanField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "gender", "date_of_birth", "national_id",
            "county", "county_name", "sub_county", "ward",
            "value_chains", "acreage",
            "group_name", "group_size",
            "preferred_channel",
            "consent_data", "consent_updates",
            "age", "is_youth",
        ]

    def validate_national_id(self, value):
        if value:
            validate_kenyan_id(value)
        return value


class MeSerializer(serializers.ModelSerializer):
    """`GET /auth/me/` — combines User + nested Profile."""
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "phone",
            "first_name", "last_name",
            "role", "preferred_language",
            "is_active", "is_verified", "last_seen_at", "created_at",
            "profile",
        ]
        read_only_fields = fields


# ─────────────────────────── Register ───────────────────────────

class RegisterSerializer(serializers.Serializer):
    """
    Accepts the full 5-step payload from the React register form.
    Steps map to fields here; validation is grouped so we can return
    field-level errors per step.
    """
    # Step 1 — Account
    email = serializers.EmailField()
    phone = PhoneNumberField(region="KE")
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    # Step 2 — Personal (all optional except first/last)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    gender = serializers.ChoiceField(
        choices=Profile.Gender.choices, required=False, allow_blank=True
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    national_id = serializers.CharField(
        required=False, allow_blank=True, max_length=20
    )

    # Step 3 — Location
    county = serializers.CharField(required=False, allow_blank=True)
    sub_county = serializers.CharField(required=False, allow_blank=True)
    ward = serializers.CharField(required=False, allow_blank=True)

    # Step 4 — Farming
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.FARMER)
    value_chains = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    acreage = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    group_name = serializers.CharField(required=False, allow_blank=True)
    group_size = serializers.CharField(required=False, allow_blank=True)

    # Step 5 — Preferences
    preferred_language = serializers.ChoiceField(choices=[("en", "English"), ("sw", "Kiswahili")], default="en")
    preferred_channel = serializers.ChoiceField(choices=Profile.Channel.choices, default=Profile.Channel.APP)
    consent_data = serializers.BooleanField()
    consent_updates = serializers.BooleanField(default=True)

    # ── Field-level validation ────────────────────────────────────

    def validate_email(self, value):
        value = value.lower().strip()
        validate_not_disallowed_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("An account with this phone number already exists.")
        return value

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        # Run Django's password validators
        try:
            validate_password(data["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        if not data.get("consent_data"):
            raise serializers.ValidationError({"consent_data": "You must accept the data policy."})

        # Youth check
        dob = data.get("date_of_birth")
        if dob:
            from datetime import date
            age = date.today().year - dob.year - (
                (date.today().month, date.today().day) < (dob.month, dob.day)
            )
            if age < 13:
                raise serializers.ValidationError({"date_of_birth": "You must be at least 13 years old."})

        return data

    # ── Create ────────────────────────────────────────────────────

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        value_chain_labels = validated_data.pop("value_chains", [])
        county_name = validated_data.pop("county", None)

        password = validated_data.pop("password")

        user = User.objects.create_user(
            email=validated_data.pop("email"),
            phone=validated_data.pop("phone"),
            password=password,
            first_name=validated_data.pop("first_name", ""),
            last_name=validated_data.pop("last_name", ""),
            role=validated_data.pop("role", User.Role.FARMER),
            preferred_language=validated_data.pop("preferred_language", "en"),
        )

        # Profile
        profile = user.profile
        for field in (
            "gender", "date_of_birth", "national_id",
            "sub_county", "ward", "acreage",
            "group_name", "group_size",
            "preferred_channel",
            "consent_data", "consent_updates",
        ):
            if field in validated_data:
                setattr(profile, field, validated_data.pop(field))

        if county_name:
            from apps.counties.models import County
            county = County.objects.filter(name__iexact=county_name).first()
            if county:
                profile.county = county

        profile.save()

        # Value chains — resolve label → Subject
        if value_chain_labels:
            from apps.courses.models import Subject
            subjects = Subject.objects.filter(label__in=value_chain_labels)
            profile.value_chains.set(subjects)

        return user

    def to_representation(self, instance):
        return {
            "user": UserSerializer(instance).data,
            "profile": ProfileSerializer(instance.profile).data,
        }


# ─────────────────────────── Login ───────────────────────────

class LoginSerializer(serializers.Serializer):
    """
    Accepts an email or phone in `identifier` plus a password. Kept
    separate from SimpleJWT's TokenObtainPairSerializer so we can
    return a richer payload on the /auth/login/ endpoint.
    """
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    remember = serializers.BooleanField(default=False)

    def validate(self, data):
        from django.contrib.auth import authenticate

        identifier = data["identifier"].strip()
        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=data["password"],
        )
        if not user:
            raise serializers.ValidationError(
                {"detail": "Invalid credentials. Check your email or phone and password."}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "This account is inactive. Contact support."}
            )
        data["user"] = user
        return data


# ─────────────────────────── Profile update ───────────────────────────

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """`PATCH /auth/me/profile/` — partial update of a learner's profile."""

    class Meta:
        model = Profile
        fields = [
            "gender", "date_of_birth", "national_id",
            "county", "sub_county", "ward",
            "value_chains", "acreage",
            "group_name", "group_size",
            "preferred_channel",
            "consent_updates",
        ]

    def validate_national_id(self, value):
        if value:
            validate_kenyan_id(value)
        return value


class UserUpdateSerializer(serializers.ModelSerializer):
    """`PATCH /auth/me/` — update name, language, etc."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "preferred_language"]


# ─────────────────────────── Password ───────────────────────────

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context["request"].user
        if not user.check_password(data["old_password"]):
            raise serializers.ValidationError({"old_password": "Current password is incorrect."})
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(data["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return data