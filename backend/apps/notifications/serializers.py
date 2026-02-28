from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "type", "channel", "status", "is_read", "created_at", "title", "message", "payload"]

    def get_title(self, obj):
        return obj.payload.get("title", obj.type)

    def get_message(self, obj):
        # Prefer 'body', then 'subject' (for emails), then generic type
        return obj.payload.get("body") or obj.payload.get("subject") or obj.type
