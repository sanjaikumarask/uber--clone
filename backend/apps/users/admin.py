from django.contrib import admin

from .models import User, DriverUser, RiderUser


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "phone", "role", "login_type", "is_active"]
    list_filter = ["role", "provider"]
    search_fields = ("phone", "email", "username")

    def login_type(self, obj):
        return obj.provider or "normal"


@admin.register(DriverUser)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "role", "login_type", "is_active")
    list_filter = ("provider", "is_active")
    search_fields = ("phone", "email", "username")

    def login_type(self, obj):
        return obj.provider or "normal"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.ROLE_DRIVER)


@admin.register(RiderUser)
class RiderAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "role", "login_type", "is_active")
    list_filter = ("provider", "is_active")
    search_fields = ("phone", "email", "username")

    def login_type(self, obj):
        return obj.provider or "normal"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.ROLE_RIDER)
