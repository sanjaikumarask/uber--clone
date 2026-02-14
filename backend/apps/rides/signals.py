from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Ride
from .serializers import RideDetailSerializer

@receiver(post_save, sender=Ride)
def ride_update_signal(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    serializer = RideDetailSerializer(instance)
    
    # Send update to ride group
    # The 'type' here matches the method name 'ride_update' in RideConsumer
    async_to_sync(channel_layer.group_send)(
        f"ride_{instance.id}",
        {
            "type": "ride_update", 
            "event": "ride_update", # This becomes message.type sent to client
            "data": {
                "ride": serializer.data
            }
        }
    )
