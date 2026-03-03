# Edge Cases: Invalid Code & Usage Limits

The Invalid Code & Usage Management system handles constraints on promotional campaigns, ensuring they remain financially sustainable and consistent for all riders.

## The Problem: Over-Usage & Expiry

In a high-intensity marketplace, an offer can be"broken"or"abused"in several ways:
- **Bulk Global Usage**: A limited-run campaign (e.g. 10,000 uses) has its last remaining uses applied by multiple users at the same millisecond.
- **Campaign Expiry**: A rider applies a code just as the `valid_to` timestamp passes.
- **User Misuse**: A single user attempts to reuse a"First Ride Free"code after they have already used it.

## Recovery Layer 1: Atomic Counters (Concurrency)

To prevent over-payout on limited-run codes:
- **Enforcement**: The `total_usage_count` is incremented using **Database F-Expressions** (`total_usage_count = F('total_usage_count') + 1`) within a transaction.
- **Conditional Check**: The update is only committed if `total_usage_count < usage_limit` at the moment of completion.

## Recovery Layer 2: Grace Periods (Expiry)

For cases where an offer expires while the rider is in-app:
- **Buffer Timing**: The system can be configured to"Grace"the application if the ride is *started* before expiry but *completed* after, provided it falls within a 15-minute window.

## The Rider Experience (In-App Feedback)

While applying an invalid code:
- **Verification Alert**: If the code is invalid (expired, wrong city, etc.), an error message is immediately returned to the app.
- **Usage Limit Banner**:"Sorry, this offer has reached its limit"message is shown.

## Atomic Transactions (Reliability)

Every set of related usage updates and ledger entries is wrapped in a **Postgres Transaction** (`transaction.atomic()`). If the ride completion fails, the usage increment is also rolled back, ensuring no"Shadow Usage"occurs.
