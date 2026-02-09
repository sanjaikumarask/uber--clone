from rest_framework import serializers
from .models import Driver


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = (
            "id",
            "status",
            "last_lat",
            "last_lng",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DriverLocationUpdateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class DriverStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Driver.Status.choices
    )
