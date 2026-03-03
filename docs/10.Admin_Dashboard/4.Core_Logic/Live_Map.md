# Live Map Updates Logic

The Live Map Updates system is a real-time broadcast engine that uses WebSockets to deliver driver location updates to the Admin Dashboard with sub-second latency.

## The Live Map Principles

The system follows a set of strict rules for streaming:

1. **Global Firehose Flow**: All driver movements are broadcast into the `admin_live_map` channel group synchronously with their ingestion from the [**Tracking module**](../../6.Tracking/Tracking_Readme.md).
2. **Low Latency Flow**: GPS updates are ingested via an API but broadcast into the WebSocket channel group immediately after processing.
3. **Group Scaling**: To prevent overloading the Browser, the Admin Dashboard can implement filtering (e.g., only show drivers in current viewport).

## The Dynamic Mapping Flow

Every coordinate update triggers a **Triple Broadcast** flow:

- **Admin Group (`admin_live_map`)**: The global live map receives the event for real-time monitoring of all online drivers.
- **Rider Group (`ride_{id}`)**: Rider app receives the event and moves the driver icon on the map.
- **Driver Group**: Optional confirmation to the driver that their location has been received and snapped correctly.

## WebSocket Channel Protocol (Live Map)

The system uses **Django Channels** for bi-directional communication:

```python
# Group Send Example
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
"admin_live_map",
{
"type":"driver.location.update",
"data": {
"id": 42,
"lat": 13.0827,
"lng": 80.2707,
"status":"ONLINE",
"phone":"9876543210"
}
}
)
```

## Atomic Transitions (Database Integrity)

While the broadcast is streaming, the database is updated with the most recent `last_snapped_lat/lng` for that driver. This ensures that if an admin refreshes the dashboard, the map is immediately populated with the correct, most recent coordinates for all online drivers.
