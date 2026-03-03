# API Endpoints: Tracking Module

The Tracking API handles high-frequency coordinate submission and real-time location retrieval.

## Driver Endpoints /api/tracking/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/location/`|Submit a raw (lat, lng) GPS ping to update status and increment distance.|
|`GET`|`/live-map/`|Get current positions of nearby drivers (used for searching).|
|`PATCH`|`/update-polyline/`|Update the `actual_route_polyline` for a ride.|

## Rider Endpoints /api/tracking/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/status/<ride_id>/`|Get the most recent snapped coordinate for a specific ride's driver.|
|`GET`|`/eta/`|Calculate a new ETA based on the driver's current position and traffic.|

## Admin Endpoints (Tracking)

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/admin/live-map/`|Firehose endpoint for monitoring all online drivers in real-time.|
|`GET`|`/admin/history/<ride_id>/`|Fetch the full path (`actual_route_polyline`) for a completed ride for safety audit.|

## Live Location Protocol

Drivers should update their location every **5-10 seconds** while `ONLINE`. 

**Request Payload:**
```json
{
"lat": 13.0827,
"lng": 80.2707,
"ride_id": 42
}
```

The system uses these updates to refresh the **Redis GEOSPATIAL** index and provide real-time tracking to riders.
- **Validation**: Coordinates outside the range (-90..90, -180..180) are rejected with `400 Bad Request`.
- **Rate Limiting**: Requests faster than the 5-second minimum are ignored to save server resources.
