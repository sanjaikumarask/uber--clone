# Database Models: Driver Incentives Module

The Driver Incentives system relies on three primary models to manage transactional, user, and audit state.

## The `DriverIncentive` Model (Config Root)

The root transactional entity representing a single incentive campaign.

### Key Fields
- `type`: `STREAK`, `PEAK`, `ZONE`.
- `title / description`: Human-readable copy for the app.
- `condition`: A JSONField for defining rule-based triggers (e.g. `{"rides_required": 5,"start_hour": 17}`).
- `reward_amount`: The amount to be credited upon completion.
- `max_per_day`: Limit for how many times the same driver can earn this incentive in a 24-hour cycle.
- `valid_from / valid_to`: The timeframe during which the incentive is active.

## `DriverIncentiveProgress` Model

Tracks a driver's live journey through a multi-step incentive.

### Streak & Count Tracking
- `driver`: The participant.
- `incentive`: The specific rule being tracked.
- `current_count`: Integer representing the driver's progress (e.g., 3 out of 5 rides).
- `completed_at`: If non-null, the driver has finished this cycle.

The `unique_together = ("driver","incentive")` constraint ensures only one active progress record exists per driver per incentive.

## `DriverIncentiveEarning` Model (Audit Trail)

The final ledger-ready record of a successful incentive completion.

### Key Fields & Persistence
- `incentive`: The root config record.
- `driver`: The recipient.
- `ride`: The specific ride ID that triggered the final completion point.
- `bonus_amount`: The final payout amount.
