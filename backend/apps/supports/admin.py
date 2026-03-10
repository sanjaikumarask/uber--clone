from django.contrib import admin

from .models import Emergency, SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "ride", "user", "reason", "status", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("description", "ride__id", "user__phone")


@admin.register(Emergency)
class EmergencyAdmin(admin.ModelAdmin):
    list_display = ("id", "ride", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("ride__id", "user__phone")
