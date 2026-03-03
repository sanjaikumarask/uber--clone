# Introduction to the Tracking Module

The Tracking module is the high-visibility layer of the Uber Clone, providing the real-time"map presence"that defines the user experience.

## Global Objectives

1. **Low-Latency Visibility**: Ensure that riders can see their driver moving smoothly on the map in real-time.
2. **Data Integrity**: Convert noisy GPS data into an accurate `actual_distance_km` for final fare calculation.
3. **Auditable History**: Maintain a persistent record of the `actual_route_polyline` for safety and support review.
4. **Anomaly Detection**: Identify when a driver is not following the suggested route or is stationary for too long.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **Real-time Layer**: Django Channels (WebSockets) using Redis as the broker.
- **Geo Logic**: Haversine formula for distance and custom snap-to-segment algorithms.
- **External APIs**: Google Roads API for high-precision snapping (optional).

## The Tracking Concept

Tracking is a continuous loop:
- **Ingest**: Collect raw Lat/Lng from the Driver's mobile app.
- **Snap**: Move the point to the closest segment of the `planned_route_polyline`.
- **Broadcast**: Push the snapped coordinate to the Rider's app via WebSocket.
- **Accumulate**: Increment the total distance travelled to ensure accurate billing at the end of the ride.
