# Eligibility Framework for Offers

The Eligibility Framework is a high-speed, multi-layer validation engine that ensures a rider is truly authorized to use a specific promotional code.

## The Problem: Promotional Misuse

In a high-intensity marketplace, an offer can be"broken"or"abused"in several ways:
- **Bulk Usage**: A single user creates multiple accounts to reuse a"First Ride Free"code.
- **Region Hopping**: A user applies an offer meant for `Chennai` while booking a ride in `Delhi`.
- **Concurrent Collision**: Two users apply the exact same"Limited Run"code (e.g. 100 uses) at the same millisecond.

## Recovery Layer 1: Multi-Point Validation

The system implements strict checks before any discount is applied:

1. **Code Check**: Is the string `UBERNEW50` active and not expired?
2. **Usage Check**: Has the global `usage_limit` (e.g. 10,000) been reached?
3. **User History**: Has this specific `user_id` already used the code `per_user_limit` times?
4. **City Targeting**: Is the ride's `city` (e.g. `Chennai`) matched with the offer's `city` list?
5. **Min Basket Value**: Is the `estimated_fare` higher than the `min_ride_value`?

## Recovery Layer 2: Atomic Counters (Concurrency)

To prevent over-payout on limited-run codes:
- **Enforcement**: The `total_usage_count` is incremented using **Database F-Expressions** (`total_usage_count = F('total_usage_count') + 1`) within a transaction.
- **Conditional Check**: The update is only committed if `total_usage_count < usage_limit` at the moment of completion.

## The Rider Experience (In-App Feedback)

While applying a code:
- **Verification Alert**: If the code is invalid (expired, wrong city, etc.), an error message is immediately returned to the app.
- **Applied Banner**: If valid, the app shows the discount and the updated `final_fare`.

## Atomic Transactions (Reliability)

Every set of related usage updates and ledger entries is wrapped in a **Postgres Transaction** (`transaction.atomic()`). If the ride completion fails, the usage increment is also rolled back, ensuring no"Shadow Usage"occurs.
