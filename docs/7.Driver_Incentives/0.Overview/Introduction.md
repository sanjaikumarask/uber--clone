# Introduction to the Driver Incentives Module

The Driver Incentives module is a key pillar of driver retention and supply-side optimization for the Uber Clone.

## Global Objectives

1. **Supply Shaping**: Incentivize drivers to be ONLINE and active during periods of high demand (Peak Hours).
2. **Increased Engagement**: Use gamification elements like"Ride Streaks"to encourage drivers to complete more trips in a single session.
3. **Local Market Control**: Deploy targeted bonuses in specific cities or geofenced zones to resolve supply shortages.
4. **Operational Consistency**: Reward drivers who maintain high completion rates and consistent platform presence.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **Condition Logic**: Flexible JSONField (`condition`) for defining rule-based incentive triggers.
- **Messaging**: Celery for asynchronous incentive progress updates and bonus settlement.
- **Real-time Broadcast**: WebSockets (Django Channels) to push progress updates to the driver's app.

## The Incentive Lifecycle

An `Incentive` flows through several states:
- **Active**: Valid and currently eligible for drivers to participate in.
- **In-Progress**: A driver has started a streak or met partial criteria for a multi-step incentive.
- **Completed**: The required criteria (e.g., 5 rides) are met.
- **Settled**: The bonus amount is credited to the driver's ledger and an `IncentiveEarning` record is created for transparency.
- **Expired**: The incentive's `valid_to` date has passed.
