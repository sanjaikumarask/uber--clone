# System Design: Notifications Module

The Notifications module is architected for maximum reliability and asynchronous delivery to prevent blocking the core ride-hailing business logic.

## Component Overview

1. **Notification API**: Public endpoints for listing user history and updating preferences.
2. **Dispatcher Service**: Centralized logic for matching notification types (e.g. `RIDE_CANCELLED`) to user preferences and preferred channels.
3. **Channel Providers**: Modular classes for interacting with external APIs (Expo Push, SendGrid, Twilio).
4. **Celery Worker Fleet**: Asynchronous fleet that executes the actual network-bound delivery requests.
5. **Audit Log & DLQ**: A persistent database store for tracking every attempt, success, or failure.

## Data Flow: Notification Dispatch

1. **Trigger**: Core logic calls the service: `send_notification(user, type, payload)`.
2. **Preferences Check**: The Dispatcher checks the user's `NotificationPreference` to see if the requested channel (e.g. `push`) is enabled.
3. **Storage**: A `Notification` record is created in the database (`status: PENDING`).
4. **Asynchronous Hand-off**: The `save()` method on the `Notification` model triggers a **Celery Task** (`deliver_notification.delay(id)`).
5. **Execution & Audit**: 
- The worker picks up the task.
- Calls the corresponding Provider class.
- Updates `status: SENT` (with `sent_at`) or `FAILED`.

## Intelligent Routing (The Router)

The module features an **Intelligent Router** that can automatically choose the best channel:
- **Critical Alerts** (e.g. OTP): Can be routed to both Push and SMS simultaneously.
- **Transactional Docs** (e.g. Receipts): Routed exclusively to Email.
- **Live Ride Updates**: Routed to Push and (optionally) via WebSocket if the app is active.
