from rest_framework import serializers
from .models import Offer, OfferUsage


class AdminOfferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = "__all__"
        read_only_fields = ("total_usage_count", "created_at")

    def validate(self, data):
        if data["valid_from"] >= data["valid_to"]:
            raise serializers.ValidationError(
                {"valid_to": "valid_to must be after valid_from."}
            )
        if data.get("discount_type") == "PERCENTAGE":
            if not (0 < data["value"] <= 100):
                raise serializers.ValidationError(
                    {"value": "Percentage discount must be between 1 and 100."}
                )
        return data


class RiderOfferListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = (
            "id",
            "code",
            "title",
            "description",
            "discount_type",
            "value",
            "max_discount",
            "min_ride_value",
            "valid_from",
            "valid_to",
            "city",
        )


class OfferUsageSerializer(serializers.ModelSerializer):
    offer_code = serializers.CharField(source="offer.code", read_only=True)

    class Meta:
        model = OfferUsage
        fields = ("id", "offer_code", "discount_applied", "created_at", "ride")
