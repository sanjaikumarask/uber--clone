from django.contrib import admin

from .models import DriverIncentive, DriverIncentiveEarning


@admin.register(DriverIncentive)
class DriverIncentiveAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "type",
        "reward_amount",
        "is_active",
        "valid_from",
        "valid_to",
        "city",
    )
    list_filter = ("type", "is_active", "city")
    search_fields = ("title", "city")


@admin.register(DriverIncentiveEarning)
class DriverIncentiveEarningAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "incentive",
        "driver",
        "ride",
        "bonus_amount",
        "created_at",
    )
    search_fields = ("incentive__title", "driver__user__username")
