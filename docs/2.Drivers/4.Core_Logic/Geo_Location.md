# Geo Location & Presence System

The Geo Location system is the high-performance core that manages driver spatial data for real-time tracking and matching.

## Redis-First Presence

While PostgreSQL stores the `last_lat/lng` for historical records, the **Matching Engine** relies entirely on **Redis GEOSPATIAL** indexes.

### Redis GEO Indexing
- **Key**: `drivers_geo:{city_id}`
- **Command**: `GEOADD`
- **Member**: Driver ID.
- **Score**: Calculated internal representation of Lat/Lng.

## The Update Cycle

1. **Incoming Pings**: Driver app sends Lat/Lng updates via API or WebSocket (every 5-10s).
2. **Snapshot**: The coordinates are saved to the `Driver` model in PostgreSQL.
3. **Active List**: The coordinates are pushed to the Redis `drivers_geo` set.
4. **Broadcast**: Coordinates are pushed to any active **Rider** tracking that ride via WebSocket.

## Search & Proximity

When a rider searches for a ride:
- The system performs a `GEORADIUS` search in Redis centered on the rider's pickup point (e.g., 10km radius).
- This returns a list of Driver IDs sorted by distance.
- This list is then passed to the [**Matching Engine**](../../3.Rides/4.Core_Logic/Matching_Engine.md) for level/score filtering.
