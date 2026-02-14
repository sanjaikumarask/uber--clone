from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_ride_update(ride_id: int, *, event: str, data: dict):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"ride_{ride_id}",
        {
            "type": "ride_update",   # 🔥 MUST MATCH consumer method
            "event": event,          # e.g. DRIVER_LOCATION_UPDATED
            "data": data,
        },
    )
