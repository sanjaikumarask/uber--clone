# Wallet System Logic

The Wallet System is a virtualized fund-management layer that allows riders to pre-load money into the platform for faster, one-click ride bookings.

## The Wallet Concept

Unlike an external bank account, the `Wallet` is an internal concept derived from the `LedgerEntry` table. 

### Balance Calculation
The system calculates a user's wallet balance by summing all of their **Credit** ledger entries and subtracting all of their **Debit** ledger entries.

```python
def get_wallet_balance(user_id):
credits = LedgerEntry.objects.filter(user_id=user_id, type='CREDIT').aggregate(Sum('amount'))['amount__sum'] or 0
debits = LedgerEntry.objects.filter(user_id=user_id, type='DEBIT').aggregate(Sum('amount'))['amount__sum'] or 0
return credits - debits
```

## The Topup Workflow

1. **Selection**: Rider chooses a topup amount (e.g., ₹500.00).
2. **Payment Stage**:
- Rider initiates an external payment via a gateway (e.g. Razorpay).
- Gateway returns a `gateway_payment_id` upon success.
3. **Credit Execution**: 
- The backend verifies the payment signature.
- A `LedgerEntry` (CREDIT) for the amount is inserted with the reason `WALLET_TOPUP`.

## Wallet-to-Ride Payment

When a rider chooses to pay for a ride using their wallet:
1. **Balance Check**: System verifies the wallet balance is $\ge$ the ride fare.
2. **Locking**: A **Postgres Row Lock** on the ledger table is acquired for the user.
3. **Debit Execution**: A `LedgerEntry` (DEBIT) for the ride fare is inserted with the reason `RIDE_PAYMENT`.

