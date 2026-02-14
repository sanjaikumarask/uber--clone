from rest_framework import serializers
from apps.rides.models import Ride


class RideDetailSerializer(serializers.ModelSerializer):
    driver = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "pickup_lat",
            "pickup_lng",
            "drop_lat",
            "drop_lng",
            "planned_distance_km",
            "planned_duration_min",
            "actual_distance_km",
            "base_fare",
            "final_fare",
            "driver",
            "created_at",
            "updated_at",
        ]

    def get_driver(self, obj):
        if not obj.driver:
            return None

        return {
            "id": obj.driver.id,
            "lat": obj.driver.last_lat,
            "lng": obj.driver.last_lng,
            "status": obj.driver.status,
        }
