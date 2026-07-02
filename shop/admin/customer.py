from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from ..models import Customer


@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = UserAdmin.fieldsets + (
        ("Verification", {"fields": ("email_verified",)}),
    )
