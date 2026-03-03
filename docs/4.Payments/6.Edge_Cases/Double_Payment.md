# Edge Cases: Double Payment Prevention

The system implements multiple overlapping layers of protection to ensure a rider is never successfully charged twice for the same ride.

## The Problem: Distributed Retries

In a high-load system, a rider might click"Pay"twice, or their network might hang, causing the app to retry. Without protection, this could result in two `CAPTURED` payments for the same `ride_id`.

## Layer 1: Database Constraints (Unique Constraint)

The `Payment` model implements a conditional unique constraint:

```python
constraints = [
models.UniqueConstraint(
fields=["ride_id"],
condition=Q(status="CAPTURED"),
name="one_captured_payment_per_ride",
)
]
```

- **Logic**: A ride can have multiple `CREATED` or `FAILED` payment records (historical attempts).
- **Enforcement**: The database will **reject** any attempt to save a second record for the same `ride_id` with a `status` of `CAPTURED`.

## Layer 2: Idempotency Headers

Every payment initialization (`create-order`) request from the mobile app is accompanied by an `X-Idempotency-Key` (typically set to `ride_{id}`).
- A retry with the same key will simply return the **existing** `gateway_order_id`, rather than initiating a new order at the gateway.

## Layer 3: Final Fare Verification

The `capture/` API endpoint performs a final state check on the **Ride** model:
- If the `Ride.payment_status` is already `PAID`, the capture call is immediately rejected with a `400 Bad Request`.

## The Recovery Workflow

In the rare event that a double capture occurs due to a gateway error (missing webhook or delayed result):
1. **Reconciliation Audit**: A background task identifies multiple `CAPTURED` calls for a single `ride_id` in the gateway logs.
2. **Auto-Refund**: The second transaction is automatically marked for `REFUND` to the rider's original payment method.
3. **Support Notification**: An alert is created on the **Admin Dashboard** for manual verification.
