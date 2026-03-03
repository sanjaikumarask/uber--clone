# Database Models: Tracking Module

The Tracking system relies on two primary models in the database to manage real-time and historical location data.

## The `Driver` Model (Tracking Fields)

The transactional Root Entity representing a driver's current status and availability.

### Tracking Fields
- **`last_lat / last_lng`**: Store the most recently received (raw) coordinates from the mobile app.
- **`status`**: dictating if the driver is currently trackable (`ONLINE` or `BUSY`).
- **`updated_at`**: Important for monitoring the"Freshness"of a driver's location.

## `Ride` Model (Historical Tracking)

Tracks the full route taken by a rider and driver from pickup to drop-off.

### Route Fields
- **`planned_route_polyline`**: The original"suggested path"from the Matching Engine.
- **`actual_route_polyline`**: The captured path taken by the driver.
- **`actual_distance_km`**: The accumulated distance calculated from snapped pings.
- **`last_snapped_lat / last_snapped_lng`**: The most recently processed point on the polyline.

## `LocationHistory` Model (Optional Audit Log)

For high-security monitoring, a separate `LocationHistory` table may be used to store every raw ping for safety audits.

### Key Fields
- `driver_id`: Recipient of the update.
- `lat / lng`: Raw coordinates.
- `ride_id`: Optional (if the driver was on a ride).
- `timestamp`: When the ping was received.
