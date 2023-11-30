from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class BaseUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "is_citizen", "is_farmer")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "is_citizen", "is_farmer")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("is_citizen", "is_farmer", "first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (("is_citizen", "is_farmer"), "username", "password1", "password2"),
            },
        ),
    )
