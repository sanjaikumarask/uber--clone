# Webhook System Logic

The Webhook System is a robust, asynchronous mechanism that handles incoming notifications from external payment gateways (e.g. Razorpay).

## The Webhook Sequence

1. **Incoming Webhook (`POST /api/webhooks/gateway/`)**
- **Validation**: The system verifies the request signature using the gateway's public key or secret.
- **Idempotency**: The system checks if the `event_id` has already been processed by checking the `WebhookEvent` table.
- **Log**: If new, it records the complete raw JSON as a `WebhookEvent` with `status: RECEIVED`.
2. **Processing Stage**: 
- An asynchronous worker (`tasks.py`) picks up the `RECEIVED` webhook.
- Matches the `event_type` (e.g., `payment.captured`, `payment.failed`).
- **Side-Effects**: Updates the `Payment` status and inserts `LedgerEntry` records as needed.
3. **Terminal State**: 
- **Success**: `WebhookEvent.status` set to `PROCESSED`.
- **Failure**: `WebhookEvent.status` set to `FAILED`. `error` is captured, and the event is queued for retry.

## Webhook Idempotency

Different gateway events are handled specifically:
- **`payment.captured`**: Updates the `Payment` record and inserts the **Ledger** entry. If already captured (from the capture API call), the webhook is `IGNORED` to prevent double-crediting.
- **`payment.failed`**: Updates the `Payment` record with the `failure_reason` and notifies the rider and driver.

## The Admin Dashboard View

Admins can monitor **Webhook Logs**:
- **Status**: CLEAR indicators for"Received,""Processed,"and"Failed."
- **Error Visibility**: Captures the specific stack trace for failed processing, allowing for quick debugging of gateway integration issues.

