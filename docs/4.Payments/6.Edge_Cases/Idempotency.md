# Edge Cases: Idempotency System

The Idempotency System is a critical network-edge protection layer that ensures a single financial request (like a payment or payout) is only executed once, even if the client retries due to network timeouts.

## The Idempotency Concept

When a client initiates a sensitive request, they include a unique `X-Idempotency-Key` (e.g., `ride_42_payment`) in the header.

### Idempotency Key Structure
Typical keys used:
- **Payment**: `ride_{id}`
- **Payout**: `payout_req_{user_id}_{timestamp}`
- **Topup**: `user_{id}_topup_{uuid}`

## The Enforcement Workflow

1. **Request Arrival (`POST /api/payments/create-order/`)**
- **Pre-Check**: The system checks the `IdempotencyKey` table (or checks for an existing `Payment` with the same `idempotency_key` field).
2. **Duplicate Detected**: 
- If a record already exists with that key, the system **DOES NOT** call the payment gateway.
- Instead, it returns the **SAME RESPONSE** (e.g., the existing `gateway_order_id`) as the first successful call.
3. **New Request**: 
- If no record exists, the system proceeds with the gateway call and commits both the gateway ID and the idempotency key to the database atomically.

## Atomic Transactions (Postgres Consistency)

To prevent a"race condition"where two simultaneous requests hit the server at the exact same millisecond:
- The `idempotency_key` field on the `Payment` and `IdempotencyKey` models is marked as **UNIQUE**.
- The database will reject the second insert attempt, ensuring that only one request is ever processed.

## Policy Rule: Terminal States

Once a payment is in a terminal state (`CAPTURED` or `REFUNDED`), the `idempotency_key` remains tied to that specific result permanently, preventing any accidental re-submission of the same ride for payment.
