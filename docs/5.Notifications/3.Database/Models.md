# Database Models: Notifications Module

The Notifications system relies on three primary models to manage transactional, user, and audit state.

## The `Notification` Model (Audit Log)

The root transactional entity representing a single delivery attempt to a specific user.

### Key Fields
- `user`: The recipient of the notification.
- `channel`: `push`, `sms`, `email`, `web`.
- `type`: `RIDE_CANCELLED`, `PAYMENT_SUCCESS`, `DRIVER_ARRIVED`, `OTP_VERIFIED`.
- `payload`: A JSONField for all specific notification data (title, body, ride_id, etc.).
- `status`: `PENDING`, `SENT`, `FAILED`.
- `is_read`: Boolean for mobile/web in-app notifications history.
- `retry_count`: Tracks how many times a failed delivery has been retried.

## `NotificationPreference` Model

Stores the user's choices regarding communication channels.

### Channel Selection
- `email_enabled`: Default: `True`.
- `sms_enabled`: Default: `False`.
- `push_enabled`: Default: `True`.

If a user turns off `push_enabled`, the **Dispatcher** should skip push delivery even if the caller specifically requested it.

## `NotificationDeadLetter` Model (Audit Trail)

The"Dead Letter Queue"(DLQ) for permanently failed notifications.

### Fault Tolerance
- **Criteria**: Any `Notification` that has reached the `retry_count` limit (e.g. 5) without success.
- **Reason**: Captured text from the provider's API (e.g.,"Invalid Device Token,""User Unsubscribed").
- **Persistence**: These records stay in the DLQ forever (unless manually cleared) for post-mortem analysis of delivery issues.
