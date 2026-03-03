# Edge Cases: Budget Limits & Incentive Expiry

The Budget & Expiry management system handles constraints on incentive campaigns, ensuring they remain financially sustainable and consistent for all drivers.

## The Problem: Over-payout & Stale Campaigns

In a high-intensity marketplace, an incentive can"break"in several ways:
- **Budget Exhaustion**: A campaign has a limit of ₹100,000.00, but so many drivers complete the streak that the total payout exceeds the budget.
- **Campaign Expiry**: A driver completes a streak just as the `valid_to` timestamp passes.
- **Multi-Incentive Collision**: A single ride qualifies for two different overlapping incentives (e.g. Peak Hour and a Streak).

## Recovery Layer 1: Daily Payout Caps (`max_per_day`)

The system implements a **Per-User Limit** on the `DriverIncentive` model:
- **Logic**: `max_per_day` limits how many times a single driver can earn the same bonus in 24 hours.
- **Enforcement**: The `IncentiveEngine` checks the `DriverIncentiveEarning` table for existing records from today before authorizing a new bonus.

## Recovery Layer 2: Hard Budget Checks (Admin Side)

For global campaigns:
- **Thresholding**: Every `DriverIncentiveEarning` has a link to the root `DriverIncentive`.
- **Auto-Deactivation**: A background task (or the ledger settle task) monitors the total sum of earnings for an ID. If it crosses the global budget, `is_active` is automatically set to `False`.

## The Driver Experience

While an incentive nears its end:
- **Rider App**: Displays"Ending Soon"or"Few Spots Remaining"on the incentive card.
- **Expiry Logic**: If a ride is *started* before expiry but *completed* after, the system can be configured to"Grace"the completion if it falls within a 15-minute buffer.
