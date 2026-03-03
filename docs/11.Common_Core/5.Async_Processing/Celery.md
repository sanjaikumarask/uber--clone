# Asynchronous Processing Logic (Celery)

The Async Processing engine is a high-performance background execution layer, specifically designed to handle long-running or computationally expensive platform operations (e.g., matching drivers, calculating fares, sending notifications).

## The Async Processing Principles

The system follows a set of strict rules for task management:

1. **Non-Blocking Backend**: The core Django API never waits for long operations. It queues a `Task` and returns an immediate 202 Created or 200 OK.
2. **Stateless Execution**: Workers retrieve tasks from **Redis**, execute them independently, and store results or trigger subsequents.
3. **Reliability (Retries)**: Tasks that fail due to transient issues (e.g. Map API timeout) are automatically queued for retry with an **Exponential Backoff**.

## The Task Workflow (Ride Matching)

1. **Enqueue Stage**: A rider POSTs a booking request. The API queues `match_driver_task` in Redis.
2. **Worker Stage**: 
- A dedicated **Celery Worker** picks up the task.
- Calls the [**Matching Engine**](../../3.Rides/4.Core_Logic/Matching_Engine.md).
- Identifies the nearest driver and sends a **Push Notification**.
3. **Completion**: 
- The task updates the `Ride` model with the assigned driver.
- A broadcast event is pushed via WebSockets to the rider's app.

## Key Task Categories

Platform tasks are divided into several priority queues:
- **Critical**: `high_priority` (Ride matching, payment capture, SOS alerts).
- **Standard**: `default` (Status updates, notifications, statistics updates).
- **Economic**: `analytics` (Revenue calculation, historical report generation).

## Atomic Transitions (Database Integrity)

The system uses `transaction.on_commit(lambda: my_task.delay(id))` to ensure that a task is only queued if the database transaction that created its data (e.g. the `Ride` record) is successfully committed.

## Future Enhancements

- **Priority Queue Expansion**: Moving from 3 to 10+ granular queues to further isolate failure domains.
- **Dead Letter Queue (DLQ)**: Automated alerting for tasks that fail after all $N$ retries (e.g. `PAYMENT_FAILURE`).
