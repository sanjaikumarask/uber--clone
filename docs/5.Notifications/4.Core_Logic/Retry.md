# Notification Retry Logic

The Retry Logic is a critical layer for ensuring delivery reliability, specifically designed to handle transient network outages or temporary downtime of external notification providers (e.g., Expo, SendGrid).

## The Retry Sequence

1. **Incoming Failure**: A Provider's `deliver()` attempt results in a `429 Too Many Requests`, `500 Server Error`, or `Connection Timed Out`.
2. **Retry Increment**: `Notification.retry_count` is incremented.
3. **Backoff Loop**: 
- The system uses **Exponential Backoff** to schedule the next delivery attempt.
- **Delay**: $2^n \times 60$ seconds (where $n$ is the current retry count).
- Sample Schedule: 1 min -> 2 min -> 4 min -> 8 min -> 16 min.
4. **Terminal Failure**: If the notification has reached its maximum retry limit (e.g. 5) after multiple hours, it is transitioned to `FAILED` and moved to the **Dead Letter Queue (DLQ)**.

## Transient vs. Permanent Errors

The Retry system distinguishes between two types of errors:
- **Transient Errors** (Retry Trigger): Issues likely to resolve automatically (e.g. `Connection Timeout`, `Rate Limit`).
- **Permanent Errors** (Instant Failure): Issues that will **never** succeed (e.g. `Invalid Push Token`, `User Blocked Our SMS Number`).

## The User Experience

While retrying:
- Riders and Drivers may experience a delay of 1-5 minutes for non-critical notifications (e.g. a receipt).
- **CRITICAL ALERT REDUNDANCY**: For mission-critical alerts (like"Driver Arrived"), the system may execute an immediate fallback to a different channel (e.g., from Push to SMS) if the primary channel fails its first retry.
