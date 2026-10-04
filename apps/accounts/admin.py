# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    extra = 0
    fieldsets = (
        ("Personal", {
            "fields": ("gender", "date_of_birth", "national_id"),
        }),
        ("Location", {
            "fields": ("county", "sub_county", "ward"),
        }),
        ("Farming", {
            "fields": ("value_chains", "acreage", "group_name", "group_size"),
        }),
        ("Preferences", {
            "fields": ("preferred_channel", "consent_data", "consent_updates"),
        }),
    )
    filter_horizontal = ("value_chains",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "email", "phone", "first_name", "last_name", "role",
        "is_active", "is_verified", "last_seen_at", "created_at",
    )
    list_filter = ("role", "is_active", "is_verified", "is_staff", "created_at")
    search_fields = ("email", "phone", "first_name", "last_name", "profile__national_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_seen_at")
    list_select_related = ("profile",)
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("id", "email", "phone", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Role & preferences"), {"fields": ("role", "preferred_language")}),
        (_("Permissions"), {
            "fields": ("is_active", "is_staff", "is_superuser", "is_verified", "groups", "user_permissions"),
        }),
        (_("Important dates"), {"fields": ("last_login", "last_seen_at", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "phone", "first_name", "last_name",
                "role", "password1", "password2",
            ),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "county", "gender", "preferred_channel", "is_youth")
    list_filter = ("county", "gender", "preferred_channel", "consent_updates")
    search_fields = ("user__email", "user__phone", "group_name", "national_id")
    autocomplete_fields = ("user",)
    filter_horizontal = ("value_chains",)