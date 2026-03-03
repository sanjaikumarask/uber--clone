# API Endpoints: Admin Dashboard Module

The Admin Dashboard API handles high-frequency coordinate submission and real-time location retrieval.

## Admin Endpoints (Dashboard History)

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/stats/summary/`|Get current platform health (Online Drivers, Active Rides, Pending Payments).|
|`GET`|`/alerts/list/`|Fetch the full history of `SystemLog` (System Alerts).|
|`GET`|`/revenue/daily/`|Get the daily, weekly, and total platform revenue.|
|`GET`|`/drivers/list/`|Comprehensive list of all registered drivers and their statuses.|
|`GET`|`/rides/list/`|Historical list of all rides (completed, cancelled, or ongoing).|

## Admin Endpoints (Live Map Firehose)

The Admin Dashboard provides high-precision monitoring of live location and safety events via WebSockets.

|Channel Group|Event Type|Description|
|:---|:---|:---|
|`admin_live_map`|`driver.location.update`|Real-time GPS movement for all online/busy drivers.|
|`admin_live_map`|`ride.booking.alert`|Notification whenever a new ride is requested.|
|`admin_live_map`|`emergency.sos.alert`|High-priority safety alert from a rider or driver.|

## Live Location Protocol (Firehose)

When a driver's location hits the platform:

**Request Payload (Broadcast):**
```json
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
```

The system immediately broadcasts this to the **Admin Dashboard** via WebSockets, ensuring sub-second visual updates on the live map.
- **Security**: All endpoints and WebSocket connections require an `admin` role authorization.
- **Rate Limiting**: The system automatically throttles broadcasts if a driver sends pings faster than the 5-second minimum.
