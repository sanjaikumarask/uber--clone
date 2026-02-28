from rest_framework import serializers
from .models import DriverIncentive, DriverIncentiveEarning


class DriverIncentiveSerializer(serializers.ModelSerializer):
    current_progress = serializers.SerializerMethodField()

    class Meta:
        model = DriverIncentive
        fields = "__all__"
        read_only_fields = ("created_at",)

    def get_current_progress(self, obj):
        request = self.context.get("request")
        if not request or not hasattr(request.user, "driver"):
            return 0
        
        driver = request.user.driver
        if obj.type == DriverIncentive.Type.STREAK:
            import redis
            from django.conf import settings
            from django.utils import timezone
            
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            today_str = timezone.now().date().isoformat()
            redis_key = f"streak:{driver.id}:{obj.id}:{today_str}"
            val = r.get(redis_key)
            return int(val) if val else 0
            
        return 0


class DriverIncentiveEarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverIncentiveEarning
        fields = "__all__"
        read_only_fields = ("created_at",)
