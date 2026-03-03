# Event Streaming with Kafka

The Kafka Event Streaming engine is a high-throughput, distributed messaging layer designed to handle massive volumes of platform events (driver location history, ride status changes, and analytics logs).

## The Event Streaming Principles

The system follows a set of strict rules for event durability and processing:

1. **Append-Only Commit Log**: All platform events are written as immutable records to Kafka topics.
2. **Stateless Consumers**: Independent services (e.g., Analytics, Fraud Detection) consume events from topics without impacting the core booking flow.
3. **Horizontal Scalability**: Topics are partitioned across multiple Kafka brokers to handle millions of events per second.

## The Event Workflow (Ride Events)

1. **Production Stage**: When a ride status changes (e.g. `ARRIVED`), a producer in the [**Rides module**](../../3.Rides/Rides_Readme.md) writes a message to the `ride-status-events` topic.
2. **Consumption Stage**:
- **Analytics Consumer**: Reads the event and updates the long-term revenue and fulfillment database.
- **Notification Consumer**: Reads the event and triggers an automated SMS/Push notification to the rider.
- **Fraud Consumer**: Analyzes the event for suspicious timing or location patterns.

## Key Kafka Topics

- **`driver-locations`**: High-frequency pings from all online drivers (used for location history and heatmaps).
- **`ride-lifecycle`**: Status changes for every ride (Booked, Assigned, Started, Completed).
- **`payment-events`**: Audit trail for all payment initiation and capture attempts.
- **`system-alerts`**: All `SystemLog` entries for centralized monitoring.

## Atomic Transitions (Database Integrity)

The system uses a **Transactional Producer** pattern where available. This ensures that the message is only published to Kafka if the corresponding database transaction (e.g. updating the ride status) is successfully committed.
