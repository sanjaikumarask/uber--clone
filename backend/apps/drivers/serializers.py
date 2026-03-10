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
    status = serializers.ChoiceField(choices=Driver.Status.choices)


class DriverDocumentSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        from .models import DriverDocument

        model = DriverDocument
        fields = [
            "id",
            "document_type",
            "status",
            "rejection_reason",
            "image_url",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.file_path
