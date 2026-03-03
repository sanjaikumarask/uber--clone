# Incentive Engine Logic

The Incentive Engine is the computational and rule-evaluation core of the system, responsible for converting driver behavior into bonus settlements.

## The Engine Evaluation Sequence

The system follows a strict set of rules for checking and applying incentives:

1. **Event Subscription**: The engine is triggered asynchronously via a Celery signal upon `Ride.status == COMPLETED`.
2. **Campaign Discovery**: 
- Fetch all `is_active=True` incentives.
- Filter them by `city` and `is_valid_now()`.
3. **Condition Assessment (JSON Rule Engine)**:
- Compare the specific completed ride's metadata (e.g. `start_time`, `pickup_geom`) with the incentive `condition`.
- **Evaluation**: 
- **Peak Hour Bonus**: Check if `ride.start_time` is within the `start_hour` and `end_hour` from the condition.
- **Streak Bonus**: Identify any existing `DriverIncentiveProgress` records and increment the `current_count`.

## How Completions are Settled

When a criteria is fully satisfied (e.g., `current_count == condition.rides_required`):

- **State Commit**: 
- A `DriverIncentiveEarning` record is inserted.
- `DriverIncentiveProgress.completed_at` is set to the current timestamp.
- **Financial Execution**: 
- A `LedgerEntry` (CREDIT) for the `reward_amount` is inserted for the driver with reason `INCENTIVE`.
- **Broadcast**: 
- A push notification ("You've earned a ₹100.00 bonus!") is sent to the driver.

## The Streak (Multi-Step) Workflow

For `STREAK` incentives:
- **Persistence**: Progress is maintained across multiple rides until the limit is reached or the incentive expires.
- **Reset Logic**: Once a streak is completed, the system can be configured to either end the progress or reset `current_count = 0` to allow the driver to start a new streak in the same session.

## Atomic Transactions (Reliability)

Every set of related progress updates and ledger entries is wrapped in a **Postgres Transaction** (`transaction.atomic()`). If the ledger insertion fails, the progress change is also rolled back, ensuring no"Shadow Earnings"occur.

## Future Enhancements

- **Complex Geographic Zones**: Moving from city-level to precise `GeoJSON` polygons for incentives in high-demand pockets (e.g. Airports).
- **Anti-Fraud Guard**: Integrating with the `abuse_detector.py` to prevent"Ghost Rides"from being counted toward streaks.
