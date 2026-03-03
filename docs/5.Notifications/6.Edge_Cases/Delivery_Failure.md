# Edge Cases: Delivery Failure & Provider Downtime

The Delivery Failure system is a robust, multi-layer mechanism that identifies and resolves disrupted notifications, ensuring communication reliability across the platform.

## The Problem: Fragmented Communication

In a high-load system, a notification can"fragment"in several ways:
- **Channel Timeout**: Our server called the provider (e.g. Expo API), but the provider's response timed out.
- **Invalid Token**: The user's device token is no longer valid, causing the provider to reject the request.
- **Network Outage**: Our server cannot reach the external provider's API.

## Recovery Layer 1: Asynchronous Retries (Reliability)

The system relies on **Exponential Backoff Retries** as the primary recovery mechanism:
1. **Failure Detected**: The Provider's `deliver()` attempt returns a transient error (e.g. `500 Server Error`).
2. **Retry Increment**: `Notification.retry_count` is incremented.
3. **Backoff Schedule**: The task is re-queued with an increasing delay (e.g., 1 min, 2 min, 4 min).

## Recovery Layer 2: Dead Letter Queue (DLQ)

For cases where a notification permanently fails (e.g., after 5 retries):
- **Move to DLQ**: The event is moved to a **Dead Letter Queue (DLQ)**.
- **Audit Record**: A persistent `NotificationDeadLetter` is created, capturing the final error message for post-mortem investigation.
- **Alerting**: The support team is notified via the **Admin Dashboard** of the failure volume.

## The User Experience

While a failure recovery is in progress:
- **Notification History**: The notification may show as"Pending"or"Failed"on the user's history screen.
- **Critical Alerts Fallback**: For mission-critical alerts (like"Driver Arrived"), the system may execute an immediate fallback to an alternative channel (e.g. from Push to SMS) if the primary channel fails its first retry.
