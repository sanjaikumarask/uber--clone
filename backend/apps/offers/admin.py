from django.contrib import admin
from .models import Offer

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "title", "discount_type", "value",
        "valid_from", "valid_to", "is_active", "city"
    )
    list_filter = ("discount_type", "is_active", "city")
    search_fields = ("title", "city")
    ordering = ("-created_at",)
