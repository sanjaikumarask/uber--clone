# System Alerts Logic

The System Alerts Engine is the authoritative internal auditing and real-time failure-notification engine of the Uber Clone platform.

## The Alert Management Principles

The system follows a set of strict rules for system-wide auditing:

1. **Fail-Always Logging**: Every critical technical failure (e.g. `PAYMENT_FAILURE`, `RIDE_STUCK`) is recorded as a `SystemLog` entry.
2. **Stateless Alerting**: Logic for triggering an alert is embedded within individual modules, while the `admin_dashboard` provides a single unified storage and broadcast point.
3. **Real-Time Firehose**: Critical alerts (type `ERROR` or `PAYMENT_FAILURE`) are broadcast via WebSockets to the Admin Dashboard for immediate attention.

## How Alerts are Classified

Alerts fall into several primary categories:

- **`ERROR`**: Critical system failures (e.g. database down, provider API error).
- **`WARNING`**: Non-critical issues (e.g. GPS drift high, slow response).
- **`PAYMENT_FAILURE`**: Automated logs whenever a rider's payment is rejected by the gateway.
- **`RIDE_STUCK`**: A specific alert for rides that remain in `SEARCHING` for $> 10$ minutes, requiring manual dispatch intervention.

## The Admin Experience (Alert Flow)

Upon system failure (e.g. from the [**Payments module**](../../4.Payments/6.Edge_Cases/Failure_Recovery.md)):
1. **Creation**: A `SystemLog` record is created with the `metadata` containing the error details.
2. **Broadcast**: An alert event is pushed via **Django Channels** to the `admin_live_map` group.
3. **Reaction**: The Admin Dashboard instantly shows a Red Alert banner with a link to investigate the specific ride or payment history.

## Atomic Transactions (Audit Integrity)

Alerts are typically inserted *outside* of the primary business transaction (`transaction.on_commit`) to ensure that even if the business logic rolls back (e.g. a payment fails and the transaction is reversed), the audit record of *why* it failed is still persisted for investigative purposes.

## Future Enhancements

- **Slack/Discord Integration**: Automatically mirror high-priority `ERROR` or `PAYMENT_FAILURE` logs to a developer Slack channel for 24/7 coverage.
- **Threshold-Based Alerting**: Only trigger an `admin_broadcast` if the same alert occurs $> N$ times in an hour.
