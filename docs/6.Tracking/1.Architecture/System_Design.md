# System Design: Tracking Module

The Tracking module is architected for maximum real-time responsiveness and high-volume data ingestion.

## Component Overview

1. **Tracking API**: Public endpoints for ingestion and live retrieval.
2. **Geo Processing Engine**: Service layer for distance calculation and snapping.
3. **Location Broadcaster**: WebSocket Consumers that stream data to specific `ride_{id}` and `admin_live_map` channel groups.
4. **Route Polyline Store**: Persistent storage of the `planned_route_polyline` and `actual_route_polyline` in the database.
5. **Deviation Alert System**: Monitors for distance between the snapped and raw coordinate.

## Data Flow: Point-to-Point

1. **GPS Update**: Driver app sends a Lat/Lng ping via POST or WebSocket.
2. **Persistence**: The most recent point is saved to the `Driver` record in PostgreSQL.
3. **Geo Processing**:
- Compare the raw point with the `planned_route_polyline`.
- **Snap**: Move the point to the nearest point on the polyline.
- **Accumulate**: Increment the `actual_distance_km` count.
4. **WebSocket Broadcast**: The processed (snapped) coordinate is pushed into the `ride_{id}` group.
5. **Rider Update**: The Rider's mobile app receives the event and updates the driver's icon position on the map immediately.

## Real-time Broadcaster (Triple Broadcast)

Every coordinate update triggers a **Triple Broadcast** flow:
- **Rider Device**: Real-time update via WebSocket for the specific `ride_{id}` group.
- **Driver App**: Confirmation that the location was received and snapped correctly.
- **Admin Live Map**: A firehose event to the global map for system-wide monitoring.
