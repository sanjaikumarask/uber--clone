# Notification Channel Providers

The Providers are modular, stateless classes that interact with external APIs to deliver notifications over specific communication channels.

## The Provider Interface

Every provider must implement a simple `deliver()` method:

```python
class PushProvider(BaseProvider):
def deliver(self, notification):
# 1. Get user's push token (e.g. Expo)
# 2. Format the message (title, body, badge)
# 3. Call the external Push API
# 4. Return success or failure response
```

## Active Supported Providers

The platform includes several built-in providers:

### Expo Push (Push Notifications)
- **Channel**: `push`.
- **Identifier**: `User.expo_push_token`.
- **Logic**: Handles message batching and returns specific error codes (e.g., `DeviceNotRegistered`).

### SendGrid / SMTP (Email)
- **Channel**: `email`.
- **Identifier**: `User.email`.
- **Logic**: Formats raw HTML receipts and welcome messages.

### Twilio / SNS (SMS)
- **Channel**: `sms`.
- **Identifier**: `User.phone`.
- **Logic**: Sends simple 160-character messages for OTP and critical alerts.

## Response Normalization

Each provider class converts the external API's response into a normalized internal format:
- **Success**: `Notification.status` updated to `SENT`.
- **Transient Failure** (e.g., timeout): `Notification.status` remains `PENDING` for retry.
- **Permanent Failure** (e.g., invalid token): `Notification.status` set to `FAILED` and moved to the [**Dead Letter Queue (DLQ)**](./DLQ.md).
