from rest_framework import serializers
from .models import Ride


class RideCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = (
            "pickup_lat",
            "pickup_lng",
            "drop_lat",
            "drop_lng",
        )
