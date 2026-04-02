from rest_framework import serializers

from .models import FAQ, SupportTicket


class SupportTicketSerializer(serializers.ModelSerializer):
    ride_details = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ride",
            "ride_details",
            "category",
            "subject",
            "reason",
            "description",
            "status",
            "resolution_note",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = ["status", "resolution_note", "resolved_at", "created_at"]

    def get_ride_details(self, obj):
        if not obj.ride:
            return None
        return {
            "pickup": obj.ride.pickup_address,
            "dropoff": obj.ride.drop_address,
            "date": obj.ride.created_at,
        }


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = "__all__"
