# apps/admin_dashboard/serializers.py
from rest_framework import serializers
from apps.rides.fare_models import FareConfig
from .models import SystemLog
from apps.drivers.models import Driver
from apps.rides.models import Ride

class FareConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FareConfig
        fields = "__all__"

class SystemLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemLog
        fields = "__all__"

class AdminDriverSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id", "full_name", "phone", "email", "status", 
            "vehicle_type", "vehicle_model", "vehicle_number", 
            "is_verified", "rating", "total_rides", "created_at"
        ]

class AdminRideSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="rider.get_full_name", read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            "id", "rider_name", "driver_name", "status", 
            "pickup_address", "drop_address", "final_fare", 
            "actual_distance_km", "created_at", "vehicle_type"
        ]

    def get_driver_name(self, obj):
        if obj.driver:
            return obj.driver.user.get_full_name()
        return "Not Assigned"
