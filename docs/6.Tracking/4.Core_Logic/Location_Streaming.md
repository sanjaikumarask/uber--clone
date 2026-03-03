# Location Streaming Logic

The Location Streaming system is a real-time broadcast engine that uses WebSockets to deliver driver GPS updates to riders and admins with sub-second latency.

## The Location Stream Principles

The system follows a set of strict rules for streaming:

1. **Low Latency Flow**: GPS updates are ingested via an API but broadcast into the WebSocket channel group immediately after processing.
2. **Stateless Broadcasting**: The broadcaster does not maintain any persistent"state."It simply pushes the latest processed coordinate to any active `ride_{id}` or `admin_live_map` group.
3. **Group Scaling**: To prevent overloading a single WebSocket group, broadcasts are limited to users who are actively watching that specific ride or the global live map.

## The Dynamic Mapping Flow

Every coordinate update triggers a **Triple Broadcast** flow:

- **Rider Group (`ride_{id}`)**: Rider app receives the event and moves the driver marker on the map.
- **Admin Group (`admin_live_map`)**: The global live map receives the event for real-time monitoring of all online drivers.
- **Driver Group**: Optional confirmation to the driver that their location has been received and snapped correctly.

## WebSocket Channel Protocol

The system uses **Django Channels** for bi-directional communication:

```python
# Group Send Example
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
f"ride_{ride_id}",
{
"type":"location.update",
"data": {
"lat": 13.0827,
"lng": 80.2707,
"heading": 45,
"status":"ONGOING"
}
}
)
```

## Atomic Transitions (Database Integrity)

While the broadcast is streaming, the database is updated with the most recent `last_snapped_lat/lng` for that ride. This ensures that if a rider refreshes their app or re-opens the map, they are immediately placed at the correct, most recent coordinate.

