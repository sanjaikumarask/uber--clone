# Ledger System Logic

The `LedgerEntry` model is the authoritative, immutable internal accounting system for the Uber Clone platform.

## The Immutable Ledger Principles

The system follows a set of strict rules for financial recording:

1. **Never Update**: Once a ledger entry is inserted, its `amount` or `type` is **NEVER** changed. If a correction is needed, a new entry of type `CORRECTION` is inserted.
2. **Every Transaction Counts**: Every financial movement (e.g., rider payment, driver commission, platform fee, penalty) is recorded as a separate entry.
3. **Unique Correlation**: Every ledger entry has a `reference` (e.g., `ride_42_commission`) to ensure that identical logic is only executed once per ride.

## How Balances are Calculated

There is no"balance"field on the `User` or `Driver` models. Instead, current balances are always derived by summing the ledger:

```sql
SELECT SUM(CASE WHEN entry_type ='CREDIT'THEN amount ELSE -amount END) AS balance
FROM LedgerEntry
WHERE user_id = 42;
```

## The Settlement Workflow (Ride Lifecycle)

Upon ride completion (`COMPLETED`):
1. **Fare Calculated**: Result (e.g., ₹250.00).
2. **Rider Payment Captured**: (₹250.00).
3. **Entry A (Debit)**: Rider Account (₹250.00) with reason `PAYMENT`.
4. **Entry B (Credit)**: Driver Earnings Account (₹200.00) with reason `DRIVER_EARNING`.
5. **Entry C (Credit)**: Platform Account (₹50.00) with reason `PLATFORM_COMMISSION`.

## Atomic Transitions (Database Integrity)

Every set of related ledger entries is wrapped in a **Postgres Transaction** (`transaction.atomic()`). If the commission calculation fails, the rider debit is also rolled back, ensuring the ledger always remains in a balanced state.

## Future Enhancements

- **Cold Storage**: Archiving ledger entries older than 2 years to a data warehouse to maintain performance on the primary DB.
- **Automated Auditing**: Background jobs that periodically verify the sum of all ledgers against the total successful payments from the gateway (e.g. Razorpay logs).

---



