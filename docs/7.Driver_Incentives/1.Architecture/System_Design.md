# System Design: Driver Incentives Module

The architecture of the Driver Incentives module is designed to handle asynchronous, rule-based progress tracking and automated financial settlement.

## Component Overview

1. **Incentive API**: Public endpoints for listing active incentives and tracking personal progress.
2. **Condition Engine**: The central logic layer that evaluates a driver's actions against specific JSON-configured rules (e.g.,"Must complete 5 rides between 5 PM and 8 PM").
3. **Progress Store (`DriverIncentiveProgress`)**: Persistent storage for tracking multi-step incentives, specifically for **Streaks**.
4. **Incentive Settlement Service**: Asynchronous service that calculates and credits bonuses to the **Ledger**.
5. **Admin Board**: Interface for configuring and monitoring incentive performance.

## Data Flow: Incentive Completion

1. **Event Completion**: A ride enters the `COMPLETED` status.
2. **Asynchronous Review**:
- A Celery task (`check_incentives`) fetches all `is_active=True` incentives.
- The system filters them by `city` and `is_valid_now()`.
3. **Condition Assessment**:
- Compare the current ride's metadata (e.g. `start_time`) with the incentive `condition`.
- For **STREAKS**: Increment the `current_count` in the `DriverIncentiveProgress` table.
4. **Completion Threshold**: 
- If the criteria are met:
- Create a `DriverIncentiveEarning` record.
- Insert a `LedgerEntry` (CREDIT) for the driver with reason `INCENTIVE`.
- Reset the streak progress as needed for the next cycle.

## Rule-Based Sharding (The JSON Condition)

The module features a flexible **Condition Field** (`JSONField`) to define complex trigger rules:

```json
{
"rides_required": 5,
"start_hour": 17,
"end_hour": 20,
"city":"Chennai",
"min_rating": 4.5
}
```

This prevents the need for hard-coding business logic for every new incentive campaign.
