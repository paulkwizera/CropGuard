from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CropGuardUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Farmer profile", {"fields": ("phone", "district", "preferred_language")}),)
    list_display = ("username", "email", "district", "preferred_language", "is_staff")
