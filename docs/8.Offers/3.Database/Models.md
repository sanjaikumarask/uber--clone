# Database Models: Offers & Promotions Module

The Offers system relies on two primary models to manage transactional, usage, and constraint state.

## The `Offer` Model (Campaign Root)

The root transactional entity representing a single promotional campaign.

### Key Fields
- `code`: A unique, case-insensitive string (e.g. `UBERNEW50`).
- `discount_type`: `FLAT` or `PERCENTAGE`.
- `value`: The amount or percentage to be discounted.
- `max_discount`: Cap for percentage-based offers.
- `min_ride_value`: Minimum required fare to apply the offer.
- **Limits**:
- `usage_limit`: Total number of times the code can be used globally.
- `per_user_limit`: How many times a single user can apply the code.
- `valid_from / valid_to`: The timeframe during which the offer is live.
- `is_active`: Manual toggle for deactivating campaigns.

## `OfferUsage` Model (Historical Audit Log)

The final record of every successfully consumed promotional code.

### Usage Fields
- `offer`: The root campaign record.
- `user`: The rider who used the code.
- `ride`: The specific ride ID where it was consumed.
- `discount_applied`: The final amount (₹) deducted from the ride fare.

## Model Constraints & Consistency

The database implements several rules to ensure promotional integrity:
- **Code Uniqueness**: Only one campaign can exist for a specific code string.
- **Usage Tracking**: The `total_usage_count` field on the `Offer` is updated atomically to prevent"Shadow Usage"under concurrent bookings.
- **User-Specific Limits**: The `OfferUsage` table is queried to ensure the `per_user_limit` is not exceeded before finalizing a ride's discount.
