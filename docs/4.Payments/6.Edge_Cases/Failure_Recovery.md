# Edge Cases: Payment Failure Recovery

The Failure Recovery system is a robust, multi-layer mechanism that identifies and resolves disrupted transactions, ensuring financial accuracy.

## The Problem: Fragmented Transactions

In a high-load system, a payment can"fragment"in several ways:
- **Phase 1 Failure**: The gateway (e.g., Razorpay) authorized the transaction, but our server crashed before calling the `capture` API.
- **Phase 2 Failure**: Our server called `capture`, but the gateway's response timed out.
- **Post-Capture Failure**: The payment was successfully captured, but the server crashed before the internal `LedgerEntry` was inserted.

## Recovery Layer 1: Webhook-Driven Completion (Reliability)

The system relies on **Asynchronous Webhooks** as the primary recovery mechanism:
1. **Incoming Webhook**: `payment.captured` event from the gateway. 
2. **Stateless Check**: If the `Payment` status in our database is still `CREATED` or `AUTHORIZED`, the webhook handler automatically transitions it to `CAPTURED` and triggers the missing `LedgerEntry` creation.
3. **Idempotency Key**: This ensures that if the server *didn't* crash and already processed the manual capture, the webhook skip-processes the call to avoid double-crediting.

## Recovery Layer 2: Periodic Pull Reconciliation (Recon Engine)

For cases where both the manual capture and the webhook were lost (e.g., universal network outage):
- **Pull Job**: A Celery task (`reconciliation.py`) runs every 60 minutes.
- **Gateway Audit**: It calls the gateway's API (`/payments`) to fetch a list of all successful transactions in the last hour.
- **Comparison**: It cross-references these against our `Payment` table. 
- **Auto-Correction**: Any transaction marked `SUCCESSFUL` on the gateway but `CREATED` in our DB is automatically updated and ledgered.

## The Rider Experience

While a recovery is in progress:
- The rider app shows a"Retrying Payment"status.
- If recovery is successful, the rider receives a delayed `PAYMENT_SUCCESS` push notification.
