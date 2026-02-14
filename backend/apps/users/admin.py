from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "role", "is_staff", "is_superuser")
    search_fields = ("phone",)
