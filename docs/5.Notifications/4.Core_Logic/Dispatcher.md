# Notification Dispatcher

The Dispatcher is the high-level logic layer that coordinates the movement of an event from a system trigger to a specific user's preferred communication channel.

## The Central Notification Logic

The Dispatcher follows a set of strict rules for every outgoing notification:

1. **Preferences Check**: The Dispatcher first retrieves the recipient's `NotificationPreference` to see if the requested channel (e.g. `push`) is enabled.
2. **Creation & Audit**: 
- A `Notification` record is inserted with the corresponding payload and `status: PENDING`.
- The `save()` method on the model triggers an **Asynchronous Celery Task** (`deliver_notification.delay(id)`).
3. **Handoff Stage**: The Celery worker picks up the notification and calls the **Provider Factory**, which returns the specific provider (Expo, SendGrid, Twilio) required for that channel.

## Intelligent Routing (The Router)

The system allows for **Multi-Channel Dispatching**:
- **Critical Alerts** (e.g."Ride Started"): Can be routed to both Push and (optionally) Email simultaneously to ensure the user receives the receipt and live tracking link.
- **Legacy Push Fallback**: If a Push notification is rejected due to an"Invalid Device Token,"the system can optionally fallback to SMS if `sms_enabled` is True.

## Example: Dispatching a Ride Cancellation

When a driver cancels a ride:
- The **Rides** app calls: `send_notification(rider_user,"RIDE_CANCELLED", payload)`.
- The **Dispatcher**:
- Records a `Notification` for `rider_user` with `channel="push"`.
- Starts a Celery task.
- The Task:
- Gets the rider's `expo_push_token`.
- Calls the Expo API.
- Updates the `Notification.status` to `SENT`.

## Atomic Transactions

The system uses `transaction.on_commit` for all Celery task triggers. This ensures that the notification is **only** scheduled if the database transaction that created the ride status change (or event) is successfully committed.
