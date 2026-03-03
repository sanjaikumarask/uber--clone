# Edge Cases: Data Lag & WebSocket Disruptions

The Data Lag & Resilience system handles constraints on promotional campaigns, ensuring they remain financially sustainable and consistent for all riders.

## The Problem: Fragmented Monitoring

In a high-intensity marketplace, a monitoring event or live-map update can"break"or be"disrupted"in several ways:
- **WebSocket Disconnection**: The Admin Dashboard loses its connection to the server.
- **Data Lag (High Volume)**: So many drivers are online that the broadcast stream experiences delay (lag).
- **System Clock Drift**: Time differences between the backend and browser cause coordinates to appear out of order.

## Recovery Layer 1: Reliable Reconnection

The Admin Dashboard frontend (browser) implements **Automatic Retry logic**:
- **Logic**: If the WebSocket connection is lost, the browser attempts an exponential backoff retry.
- **Catch-Up**: Upon successful reconnection, the dashboard makes a REST API call (`/api/admin/live-map/history/`) to"catch up"on any missing alerts or coordinates from the last 60 seconds.

## Recovery Layer 2: Firehose Throttling (Volume Control)

For cases where event volume exceeds browser limits:
- **Throttling**: The dashboard frontend limits the frequency of map renders (e.g. to 1 per second) regardless of how many pings are received from the WebSocket.
- **Batching**: The backend can be configured to"Group"multiple coordinates into a single broadcast message (e.g. send updates for all online drivers as one JSON list every 2 seconds).

## The Admin Experience (In-App Feedback)

While of a monitoring disruption:
- **Connection Indicator**: The dashboard shows a"Connecting..."or"Live Map Disconnected"banner.
- **Delayed Alert Badge**: Alerts that were not successfully broadcast are flagged with a"Synchronized Late"badge in the audit history.

## Atomic Transactions (Audit Integrity)

System alerts are inserted *outside* of the primary business transaction (`transaction.on_commit`) to ensure that even if the business logic rolls back (e.g. a payment fails and the transaction is reversed), the audit record of *why* it failed is still persisted for investigative purposes.
