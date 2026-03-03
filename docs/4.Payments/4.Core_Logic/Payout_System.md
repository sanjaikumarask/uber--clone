# Payout System Logic

The Payout System manages the withdrawal of earned funds from the platform to the driver's linked bank account.

## The Payout Sequence

1. **Request Stage (`POST /api/payments/payouts/request/`)**
- **Balance Check**: The system calculates the driver's current balance from the `LedgerEntry` table. 
- **Minimum Withdrawal**: The system enforces a minimum (e.g., ₹500.00) for all payout requests.
- **Creation**: A `Payout` record is created (`status: REQUESTED`).
2. **Processing Stage**: 
- An asynchronous worker (`tasks.py`) picks up the requested payout.
- Calls the integrated payment gateway's (e.g. Razorpay Payouts) API to move funds.
- `status` is updated to `PROCESSING`.
3. **Terminal State**: 
- **Success**: `status` set to `PAID`. A `LedgerEntry` (DEBIT) for the withdrawal amount is inserted.
- **Failure**: `status` set to `FAILED`. `failure_reason` is captured, and the driver is notified. No funds are debited from the platform.

## Commission & Fees

The Payout Engine automatically handles platform economics:
- **Platform Cut**: Commission is typically deducted upon ride completion (`DRIVER_EARNING` vs `PAYMENT`).
- **Withdrawal Fee**: A flat per-withdrawal fee (e.g., ₹10.00) may be deducted from the driver's request as a `WITHDRAWAL_FEE` ledger entry.

## The Driver Experience (Audit Trail)

Drivers can see their `Payout` history on the **Earnings** screen:
- **Status**: CLEAR indicators for"Requested,""In Progress,"and"Paid."
- **Reference**: Gateway-provided transaction IDs are visible for support calls.
