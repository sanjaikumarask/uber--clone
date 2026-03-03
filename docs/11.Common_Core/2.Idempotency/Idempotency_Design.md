# Idempotency Design

The Idempotency system is a critical layer for ensuring transactional integrity across the entire Uber Clone platform, specifically designed to handle duplicate requests at the API gateway level.

## The Idempotency Principles

The system follows a set of strict rules for unique transaction enforcement:

1. **Unique Request Keys**: Every sensitive state-changing request (e.g. payment initiation, ride status update) must include a unique `X-Idempotency-Key` or a ride-specific correlation ID.
2. **Stateless Enforcement**: If the system receives a request with an existing key, it returns the **SAME RESPONSE** (e.g. the existing `PaymentID`) from the first successful call.
3. **Atomic Consistency**: The system uses **Postgres Unique Constraints** for `idempotency_key` fields to ensure only one record is created synchronously.

## The Enforcement Workflow (Rider Payment)

1. **Request Arrival (`POST /api/payments/create-order/`)**
- **Pre-Check**: The system checks for an existing `Payment` with the same `idempotency_key` (e.g. `ride_42_payment`).
2. **Duplicate Detected**: 
- If a record already exists with that key, the system **DOES NOT** call the payment gateway.
- Instead, it returns the **SAME RESPONSE** (e.g., the existing `gateway_order_id`) as the first successful call.
3. **New Request**: 
- If no record exists, the system proceeds with the gateway call and commits both the gateway ID and the idempotency key to the database atomically.

## Examples: Key Structures

- **Payment Initiation**: `ride_{id}_payment`
- **Payout Request**: `driver_{id}_payout_{timestamp}`
- **Ride Match Acceptance**: `ride_{id}_assignment`

## Atomic Transitions (Database Integrity)

The system stores the mapping of `idempotency_key` to its corresponding `SerializedResponse` in **Redis** for 24 hours. This allows the system to return a"Duplicate"response infinitely without hitting the primary PostgreSQL database for every retry.
