# Geo Processing Logic

The Geo Processing engine is the computational core of the Tracking system, responsible for converting raw GPS data into actionable insights for billing and mapping.

## The Distance Formula (Haversine)

The system uses the **Haversine Formula** to calculate the distance between two (lat, lng) pairs over a spherical earth.

```python
def haversine_m(lat1, lng1, lat2, lng2):
R = 6371000 # Earth radius in meters
# ... calculation ...
return distance_m
```

## Distance Accumulation Workflow

1. **Receive Ping**: (lat2, lng2).
2. **Retrieve Previous**: `last_snapped_lat/lng` from the `Ride` model.
3. **Calculation**: `dist = haversine_m(prev, curr)`.
4. **Increment**: `Ride.actual_distance_km += (dist / 1000)`.
5. **Audit**: The new coordinate is appended to the `actual_route_polyline`.

## Administrative Boundaries (Geofencing)

The logic includes basic geofencing checks to ensure:
- A driver is within the allowed operating city (e.g. `Chennai`).
- Notifications are triggered when a driver crosses into a"Surge Pricing"zone.
