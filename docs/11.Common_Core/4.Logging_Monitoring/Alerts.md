# Common Alerting Framework

The Common Alerting Framework is a unified messaging layer for capturing and dispatching critical technical and operational notifications across the entire platform.

## The Alerting Principles

The system follows a set of strict rules for incident response:

1. **Uniform Logging**: Every critical failure across all modules is routed through the [**Common Logging system**](./Logging.md).
2. **Real-time Dispatch**: High-priority alerts (`ERROR`, `PAYMENT_FAILURE`, `SPOOF`) are immediately pushed to the [**Admin Dashboard**](../../10.Admin_Dashboard/4.Core_Logic/Alerts.md) via WebSockets.
3. **Severity Classification**: Alerts are categorized into `INFO`, `WARNING`, `ERROR`, and `CRITICAL` levels.

## The Alerting Workflow

1. **Trigger**: Logic in a business module (e.g. `fraud.py`) identifies a violation.
2. **Log Creation**: `logger.error("Fraud Detected", extra={"ride_id": 42})` is called.
3. **Dashboard Update**: The [**Admin Firehose**](../../10.Admin_Dashboard/2.API/Endpoints.md) receives the event via WebSockets and displays a high-visibility alert banner.

## Atomic Transitions (Audit Integrity)

Alerts are typically inserted *outside* of the primary business transaction (`transaction.on_commit`) to ensure that even if the business logic rolls back (e.g. a payment fails and the transaction is reversed), the audit record of *why* it failed is still persisted for investigative purposes.

## Future Enhancements

- **Multi-Channel Routing**: Automatically mirror high-priority alerts to PagerDuty or Slack based on the `Severity` level and `Module`.
- **Automated Remediation**: Triggering"Self-Healing"tasks (e.g. restarting a stuck worker) when specific alert patterns are detected.
