from rest_framework import serializers

from apps.rides.models import Ride


class RideDetailSerializer(serializers.ModelSerializer):
    driver = serializers.SerializerMethodField()
    rider = serializers.SerializerMethodField()
    polyline = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "pickup_lat",
            "pickup_lng",
            "pickup_address",
            "drop_lat",
            "drop_lng",
            "drop_address",
            "vehicle_type",
            "polyline",
            "planned_route_polyline",
            "planned_distance_km",
            "planned_duration_min",
            "actual_distance_km",
            "base_fare",
            "final_fare",
            "discount_amount",
            "driver_bonus",
            "applied_offer",
            "driver",
            "rider",
            "otp_code",
            "created_at",
            "updated_at",
            "otp_verified_at",
            "arrived_at",
            "completed_at",
            "cancelled_at",
            "actual_route_polyline",
        ]

    def get_polyline(self, obj):
        return obj.planned_route_polyline

    def get_driver(self, obj):
        if not obj.driver:
            return None

        return {
            "id": obj.driver.id,
            "lat": obj.driver.last_lat,
            "lng": obj.driver.last_lng,
            "status": obj.driver.status,
            "vehicle_model": obj.driver.vehicle_model,
            "vehicle_number": obj.driver.vehicle_number,
            "user": {
                "first_name": obj.driver.user.first_name,
                "last_name": obj.driver.user.last_name,
                "phone": obj.driver.user.phone,
            },
        }

    def get_rider(self, obj):
        return {
            "phone": obj.rider.phone,
            "name": f"{obj.rider.first_name} {obj.rider.last_name}".strip(),
        }
