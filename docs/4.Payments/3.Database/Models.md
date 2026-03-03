# Database Models: Payments Module

The Payments system relies on four primary models to manage transactional, accounting, and payout state.

## The `Payment` Model

The transactional Root Entity representing a single funds-capture request.

### Key Fields
- `status`: `CREATED`, `AUTHORIZED`, `CAPTURED`, `FAILED`, `REFUNDED`.
- `amount`: Total currency value (e.g. INR).
- `gateway_order_id / gateway_payment_id`: Correlation IDs with the payment gateway (e.g. Razorpay).
- `idempotency_key`: Unique string used to prevent duplicate requests (usually maps to `ride_id`).

## `LedgerEntry` Model (IMMUTABLE)

The internal accounting system. **NEVER UPDATE — ONLY INSERT.**

### Entry Rules & Persistence
- **Type**: `CREDIT`, `DEBIT`, `HOLD`, `RELEASE`.
- **Reason**: `PAYMENT`, `DRIVER_EARNING`, `PLATFORM_COMMISSION`, `PENALTY`, `REFUND`.
- **Reference**: A unique correlation key used to ensure that a ledger entry is only created once per event (e.g., `ride_42_commission`).

## `Payout` Model

Tracks fund withdrawals from the platform to a driver's bank account.

### Key Fields & Status
- `amount`: Gross withdrawal amount.
- `fee`: Platform withdrawal fee.
- `net_amount`: What actually hits the driver's bank account.
- `status`: `REQUESTED`, `PROCESSING`, `PAID`, `FAILED`.

## `WebhookEvent` Model

The Audit Log for all incoming gateway notifications.

### Auditing Workflow
- **`received_at`**: Timestamp when the webhook hit our API.
- **`payload`**: Complete raw JSON from the gateway.
- **`status`**: `RECEIVED`, `PROCESSED`, `FAILED`, `IGNORED`.
- **`processed_at`**: Timestamp when the side effects (e.g., updating Payment status) were successfully committed.

