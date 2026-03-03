# Refund System Logic

The Refund System manages the process of returning funds to a rider's original payment method or their platform wallet.

## The Refund Sequence

1. **Request Stage (`POST /api/payments/refund/`)**
- **Validation**: The system checks if the `Payment` record is `CAPTURED`.
- **Refundable Balance**: The system ensures the requested amount is $\le$ the `refundable_amount` (`amount - refunded_amount`).
- **Creation**: A request is created in the internal `Refund` (or `Payment` update) logic.
2. **Processing Stage**: 
- An asynchronous worker (`tasks.py`) calls the integrated gateway (e.g. Razorpay) `/refunds` API.
- The `Payment` status is updated to `PARTIALLY_REFUNDED` or `REFUNDED`.
3. **Terminal State**: 
- **Success**: A `LedgerEntry` (CREDIT) for the refund amount is inserted for the Rider.
- **Reversal**: A corresponding `LedgerEntry` (DEBIT) for the Driver earnings and platform commission is recorded to reverse the original earnings.

## Refund Policy Rules

Different refund scenarios are handled distinctly:
- **Full Refund**: Typically for a ride that was cancelled by the driver or for system failures.
- **Partial Refund**: For cases where the ride was completed but the rider encountered a legitimate service issue (e.g., poor driver behavior).
- **Rider Wallet Refund**: If the original payment method is not available, funds can be credited to the internal platform `Wallet`.

## The Rider Experience

Riders can view `Refund` history in their **Ride Details** or **Transaction History**:
- **Status**: CLEAR indicators for"Refund Initiated,""Refunded."
- **Timeline**: Informs riders that refunds can take 5-7 business days to reflect in their bank account.
