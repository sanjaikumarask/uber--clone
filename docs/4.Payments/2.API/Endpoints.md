# API Endpoints: Payments Module

The Payments API provides a secure and comprehensive set of endpoints for riders, drivers, and admins.

## Rider Endpoints /api/payments/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/create-order/`|Initialize a payment for a completed ride and get the gateway order ID.|
|`POST`|`/capture/`|Finalize a payment after successful frontend authorization.|
|`GET`|`/history/`|List all historical payments and their status.|
|`GET`|`/wallet/balance/`|Get current wallet balance (Total Ledger Credit - Debit).|
|`POST`|`/wallet/topup/`|Add funds to the internal wallet.|
|`GET`|`/ledger/`|Get an itemized list of all ledger entries for the rider.|

## Driver Endpoints /api/payments/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/earnings/`|Get a summary of daily, weekly, and total earnings.|
|`GET`|`/payouts/`|List all past and pending payout requests.|
|`POST`|`/payouts/request/`|Initiate a withdrawal of earned funds to the driver's bank account.|

## Admin & Webhook Endpoints

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/webhook/razorpay/`|Endpoint for receiving asynchronous gateway notifications.|
|`GET`|`/admin/recon/`|Dashboard for monitoring ledger drift and reconciliation status.|
|`POST`|`/admin/refund/`|Manually initiate a refund for a specific payment.|

## Gateway Integration Logic

Most payments follow a **Two-Phase Commit**:
1. **Initialize**: Call `create-order/` to get a `gateway_order_id`.
2. **Verify & Capture**: Once the client-facing UI (e.g. Razorpay modal) is successful, call `capture/` with the `gateway_payment_id` and `gateway_signature`.

The system uses these steps to update the **Payment** status and create the required **LedgerEntry** records atomically.
