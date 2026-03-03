# Edge Cases: GPS Drift & Map Jitter

The GPS Drift & Map Jitter mitigation system is a critical layer for ensuring visual smoothness and accurate distance tracking, especially in high-density urban environments with significant signal interference.

## The Problem: GPS Inaccuracy

GPS sensors on mobile devices frequently exhibit"Drift"or"Jitter"in several ways:
- **Drift**: A driver is stationary at a red light, but the GPS pings are moving around in a 5-10 meter radius (jitter).
- **Multipath Error**: Tall buildings in an"Urban Canyon"(like Chennai/Mumbai) can reflect signals, causing the GPS to move the driver icon 50+ meters away from their actual location on a parallel street.
- **Tunnel/Underpass**: GPS signal is lost entirely when a driver enters a tunnel or underpass.

## Recovery Layer 1: Distance-Based Throttling (Smoothing)

The system uses **Distance Thresholds** to filter out small-scale jitter:
1. **Incoming Ping**: (lat2, lng2).
2. **Comparison**: The system calculates the distance from the `last_lat/lng`. 
3. **Action**: If the distance is `< 3-5 meters`, the new coordinate is **IGNORED** for distance accumulation (it's assumed to be jitter).

## Recovery Layer 2: Snap-to-Route Correction (Drift)

For multipath errors (where the GPS deviates from the road):
- **Logic**: The system compares the raw point with the nearest segment of the `planned_route_polyline`.
- **Snapping**: If the distance is `< 50 meters`, the point is"pulled"onto the road.
- **Detour Detection**: If the distance is `> 50 meters`, the system assumes a legitimate detour and **DOES NOT** snap, but instead calculates a new path and alerts the rider.

## The Rider Experience

While a drift recovery or detour occurs:
- **Map Animation**: The driver's icon on the map moves smoothly to its new snapped position using **Linear Interpolation**.
- **ETA Change**: The Rider app shows a"Rerouting..."message and a new ETA is provided to reflect the detour.

