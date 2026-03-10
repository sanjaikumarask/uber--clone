from django.contrib import admin

from .fare_models import FareConfig
from .models import Ride


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "rider",
        "driver",
        "status",
        "vehicle_type",
        "final_fare",
        "start_time",
        "end_time",
        "created_at",
    )
    list_filter = ("status", "vehicle_type")
    readonly_fields = (
        "start_time",
        "end_time",
        "waiting_seconds",
        "actual_distance_km",
        "final_fare",
    )
    search_fields = ("rider__username", "driver__user__username", "pickup_address")


@admin.register(FareConfig)
class FareConfigAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_type",
        "base_fare",
        "base_distance_km",
        "per_km_rate",
        "waiting_free_minutes",
        "waiting_per_minute",
        "surge_multiplier",
        "minimum_fare",
        "platform_commission_pct",
        "is_active",
        "updated_at",
    )
    list_editable = (
        "base_fare",
        "per_km_rate",
        "waiting_per_minute",
        "surge_multiplier",
        "minimum_fare",
        "is_active",
    )
    readonly_fields = ("updated_at",)

    fieldsets = (
        (
            "Vehicle",
            {
                "fields": ("vehicle_type", "is_active"),
            },
        ),
        (
            "Base Fare",
            {
                "fields": ("base_fare", "base_distance_km"),
                "description": "Flat charge for every ride. Includes first base_distance_km for free.",
            },
        ),
        (
            "Distance Pricing",
            {
                "fields": ("per_km_rate", "per_min_rate"),
            },
        ),
        (
            "Waiting Charges",
            {
                "fields": ("waiting_free_minutes", "waiting_per_minute"),
                "description": "Driver waiting time at pickup. First N minutes are free.",
            },
        ),
        (
            "Surge & Floor",
            {
                "fields": ("surge_multiplier", "minimum_fare"),
            },
        ),
        (
            "Platform",
            {
                "fields": ("platform_commission_pct",),
            },
        ),
        (
            "Audit",
            {
                "fields": ("updated_at",),
            },
        ),
    )
