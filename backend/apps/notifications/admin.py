from django.contrib import admin
from .models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "channel", "status", "created_at")
    list_filter = ("channel", "status")

admin.site.register(NotificationPreference)
