from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import DriverIncentive
from .serializers import DriverIncentiveSerializer


@receiver(post_save, sender=DriverIncentive)
def notify_incentive_change(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    serializer = DriverIncentiveSerializer(instance)
    
    async_to_sync(channel_layer.group_send)(
        "driver_incentives",
        {
            "type": "incentive_update",
            "content": serializer.data
        }
    )
