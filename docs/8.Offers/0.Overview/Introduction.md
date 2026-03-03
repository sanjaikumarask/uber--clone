# Introduction to the Offers Module

The Offers module is a critical marketing and growth tool for the Uber Clone platform, enabling targeted promotions and rider incentives.

## Global Objectives

1. **Rider Acquisition**: Incentivize new users with"First Ride"flat discounts.
2. **Rider Retention**: Reward consistent users with percentage-based offers for repetitive bookings.
3. **Market Shaping**: Drive demand in specific cities or during specific time windows with targeted promo codes.
4. **Economic Integrity**: Enforce strict usage limits and maximum discount caps to protect platform revenue.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **Validation Engine**: Stateless logic for checking code validity, usage history, and constraints.
- **Security**: Idempotency and atomic counters to prevent over-usage of limited-run promo codes.

## The Offer Concept

An `Offer` is a stateful entity defined by its `code` and set of constraints. It flows through several logical states:
- **Active**: Valid for use if within the `valid_from` and `valid_to` window and under the `usage_limit`.
- **Applied**: A code has been successfully validated and attached to a specific `Ride`.
- **Consumed**: The ride has been completed, a `LedgerEntry` for the discount has been recorded, and the `total_usage_count` has been incremented.
- **Inactive/Expired**: No longer valid for new ride applications.
