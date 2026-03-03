# Logging & Monitoring Infrastructure

The Logging & Monitoring system is the foundational observability layer, specifically designed to capture and centralize technical health and performance data for the Uber Clone platform.

## The Observability Principles

The system follows a set of strict rules for audit and diagnostic data:

1. **Structured JSON Logging**: Every system log is formatted as a JSON object (via `python-json-logger`) to facilitate parsing and alerting in modern log aggregators.
2. **Stateless Health Aggregation**: Distributed backend nodes feed into a centralized **Redis** or **Elasticsearch** sink for real-time visibility.
3. **Cross-Module Correlation**: Every log event includes a `request_id`, `ride_id`, or `driver_id` to allow for end-to-end tracing of a single transaction.

## The Logging Workflow (`logging.py`)

1. **Event Capture**: A developer calls `logger.error(message, extra={"ride_id": 42})`.
2. **Context Injection**: The `CorrelationMiddleware` automatically injects the `request_id` into the log record.
3. **Serialization**: The record is formatted into a single-line JSON string: `{"message":"Payment Failed","ride_id": 42,"level":"ERROR","request_id":"8ebe9b..."}`.
4. **Transport**: Logs are written to `stdout` for collectors to pick up and forward to the [**Admin Dashboard**](../../10.Admin_Dashboard/4.Core_Logic/Alerts.md).

## Key Metrics & Alerts

The system tracks several critical platform metrics:
- **API Latency**: Response time (P99) for core endpoints like `/rides/book/`.
- **Error Rate (%)**: Percentage of requests returning $4xx$ or $5xx$ errors.
- **DB Pool Saturation**: Number of active versus total available database connections.
- **Queue Depth**: The number of pending tasks in the **Celery/Redis** queue (monitored for backpressure).

## Atomic Transitions (Audit Integrity)

System logs are captured *asynchronously* from the primary business logic to ensure that an error during logging (e.g. disk full) does not crash the core ride booking process.

## Future Enhancements

- **OpenTelemetry Integration**: Moving to full distributed tracing with **Jaeger** or **Honeycomb**.
- **Predictive Alerting**: Using historical trends to alert *before* a failure occurs (e.g."DB connections rising faster than normal").
