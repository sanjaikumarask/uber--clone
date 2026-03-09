from django.contrib import admin

from .models import Driver, DriverStats


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "level", "updated_at")
    list_filter = ("status", "level")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DriverStats)
class DriverStatsAdmin(admin.ModelAdmin):
    list_display = (
        "driver",
        "score",
        "trust_score",
        "acceptance_rate",
        "cancellation_rate",
    )
    readonly_fields = (
        "offered_rides",
        "accepted_rides",
        "cancelled_rides",
        "completed_rides",
    )

    def has_delete_permission(self, request, obj=None):
        return False
