# Introduction to the Payments Module

The Payments module is the financial heart of the Uber Clone platform, managing more than just simple transactions.

## Global Objectives

1. **Financial Accuracy**: Ensure that every rupee charged to the rider is correctly accounted for across driver earnings and platform fees.
2. **Stateless Reliability**: Use idempotent tokens and webhooks to handle payments across distributed systems.
3. **Trust & Transparency**: Maintain a transparent, immutable ledger (`LedgerEntry`) for both riders and drivers to view their financial history.
4. **Automated Lifecycle**: Seamlessly transition from ride completion to fare calculation, payment capture, and driver payout.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **Payment Gateway**: Razorpay (Integration ready).
- **Messaging**: Celery for asynchronous reconciliation and payout processing.
- **Security**: Idempotency keys and signature verification for all incoming webhooks.

## The Payment Concept

A `Payment` is a state-managed entity that tracks its journey from `CREATED` to `CAPTURED` or `FAILED`. Every successful payment triggers:
- **Ledger Updates**: Debit for the rider, credit for the driver.
- **Commission Split**: Calculation and recording of the platform's cut.
- **Earnings Record**: Specific metadata for the driver's daily/weekly summary.
