# Operational Metrics

The Metrics system is a decentralized health-monitoring layer, specifically designed to capture and centralize numerical performance data for the Uber Clone platform.

## The Metrics Principles

The system follows a set of strict rules for audit and diagnostic data:

1. **Prometheus Format**: Every backend node and worker exports metrics in a format compatible with Prometheus.
2. **Stateless Aggregation**: Distributed backend nodes feed into a centralized **Prometheus** instance for real-time visibility.
3. **Cross-Module Correlation**: Every metric event includes the originating module (e.g. `rides`, `payments`) to allow for end-to-end tracing of platform health.

## Key Performance Indicators (KPIs)

The system tracks several critical platform metrics:
- **Booking Throughput**: Number of rides created per minute.
- **Assignment Success Rate**: % of rides successfully assigned to a driver.
- **Payment Failure Rate**: % of payment attempts that return an error.
- **Worker Capacity**: % saturation of the **Celery** worker pool.

## The Monitoring Flow

1. **Collection**: The backend middleware records the latency and result of every API call.
2. **Scraping**: A Prometheus server polls the `/metrics` endpoint of every backend instance.
3. **Visualization**: Data is pushed to [**Grafana Dashboards**](../../10.Admin_Dashboard/0.Overview/Introduction.md) for real-time operational monitoring.

## Atomic Transitions (Audit Integrity)

Metrics are captured *asynchronously* within the request-response lifecycle using a light-weight in-memory counter. This ensures that the monitoring system itself does not add significant latency to the platform's core booking process.

## Future Enhancements

- **Predictive Scaling**: Automatically spinning up new backend instances if the **CPU** or **DB Pool Saturation** metrics exceed a 75% threshold.
- **User-Segment Metrics**: Tracking performance metrics specifically for"Power Users"versus new riders.
