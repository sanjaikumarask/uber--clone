# Notification Dead Letter Queue (DLQ)

The Dead Letter Queue (DLQ) is a persistent, separate storage system for permanently failed notifications, specifically designed to handle notifications that have reached their retry mapping limit (e.g. 5 attempts) without success.

## The DLQ Concept

A `Notification` record is moved to the **Dead Letter Queue** by being copied to the `NotificationDeadLetter` table.

### Purpose of the DLQ
- **No More Retries**: Any notification that has failed 5 times already is highly unlikely to succeed on its own.
- **Error Visibility**: Captures the final error message from the provider (e.g."User Unsubscribed,""Invalid Device Token").
- **Manual Recovery**: Allows for human intervention, such as updating a user's phone number or push token if it's repeatedly failing.

## The Enforcement Workflow

1. **Terminal Failure**: If a `Notification` has reached its `retry_limit` (e.g. 5) after multiple hours, the system:
- Sets `Notification.status = FAILED`.
- Inserts a new `NotificationDeadLetter` record.
2. **Alerting & Monitoring**: 
- The system identifies high volumes of DLQ records and alerts the **Admin Dashboard**.
- The `failure_reason` is made visible to the Support Team for quick investigation of channel provider outages.
3. **Correction**:
- Once a specific channel issue is resolved (e.g. invalid push token), the system can manually trigger a `retry_payouts` or `retry_notifications` task for the affected DLQ group.

## Dead Letter Queue Persistence

The DLQ is intended to be a **Permanent Audit Trail**:
- Unlike normal notification history (which may be archived after 30 days), DLQ records are kept indefinitely until manually cleared.
- Provides a"Post-Mortem"view of system-wide notification health.
