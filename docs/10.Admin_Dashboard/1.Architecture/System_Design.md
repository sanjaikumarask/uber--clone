# System Design: Admin Dashboard Module

The Admin Dashboard is architected for maximum real-time responsiveness and high-precision monitoring of thousands of concurrent backend events.

## Component Overview

1. **Dashboard API**: Public endpoints for listing history and viewing system health summaries.
2. **Live Map Broadcaster**: High-performance WebSocket Consumer that pushes driver and ride coordinates to the frontend.
3. **Alerting Engine**: Centralized logging logic for any system failure (e.g. `PAYMENT_FAILURE`, `RIDE_STUCK`).
4. **Admin UI**: A dedicated, authenticated React/Next.js dashboard with map-based visualization.
5. **Analytics Service**: Layer for calculating daily, weekly, and total revenue on the fly.

## Data Flow: Real-time Firehose

1. **Incoming Update**: A driver's location hits the [**Tracking module**](../../6.Tracking/Tracking_Readme.md).
2. **Redis Intermediary**: The updated (snapped) coordinate is stored temporarily in Redis.
3. **WebSocket Broadcast**: 
- The system pushes the event into the `admin_live_map` group in **Django Channels**.
- The Admin Dashboard (Browser) receives the `driver.location.update` message.
- **Frontend Update**: The React map component immediately moves the driver's icon with sub-second latency.

## System Alert Monitoring (The Firehose)

Errors from any module are routed to the `admin_dashboard.models.SystemLog`:
- **`ERROR`**: Critical system failures (e.g. database down, provider API error).
- **`WARNING`**: Non-critical issues (e.g. GPS drift high, slow response).
- **`PAYMENT_FAILURE`**: Automated logs whenever a rider's payment is rejected.
- **`RIDE_STUCK`**: A specific alert for rides that remain in `SEARCHING` for $> 10$ minutes.
