# System Design: Payments Module

The Payments module is architected for maximum financial integrity and resilience against network-level transaction failures.

## Component Overview

1. **Payment API**: Manages payment initialization, capture requests, and user-facing dashboards.
2. **Ledger Engine**: The authoritative internal accounting system (`LedgerEntry`).
3. **Webhook Processor**: Stateless, idempotent handling of asynchronous gateway notifications.
4. **Payout Engine**: Service layer for generating driver payouts and managing withdrawals.
5. **Reconciliation Engine**: Asynchronous service that audits total ledger sums against gateway success logs.

## Data Flow: Payment Capture

1. **Creation**: Rider initiates payment for a completed ride. A `Payment` record is created (`status: CREATED`).
2. **Authorization**: The gateway (e.g. Razorpay) authorizes the transaction.
3. **Capture (Server-Side)**: 
- The backend verifies the signature.
- Calls the gateway to capture funds.
- Updates `status: CAPTURED`.
4. **Accounting (Post-Capture)**:
- Insert `LedgerEntry` (Debit) for Rider.
- Insert `LedgerEntry` (Credit) for Driver earnings.
- Insert `LedgerEntry` (Credit) for Platform commission.

## The Ledger (Triple-Entry Principle)

The platform follows a **Triple-Entry Accounting** model:
- **Entry 1**: The Payment Gateway's record (External).
- **Entry 2**: The `Payment` model record (Transactional).
- **Entry 3**: The `LedgerEntry` audit trail (Internal Accounting).

An automated reconciliation task runs every 10 minutes to ensure that the sum of these three entries for every ride ID equals zero.
