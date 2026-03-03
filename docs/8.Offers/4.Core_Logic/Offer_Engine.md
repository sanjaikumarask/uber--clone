# Offer Engine Logic

The Offer Engine is the computational and rule-evaluation core of the system, responsible for converting promotional codes into actionable ride discounts.

## The Calculation Sequence

The system follows a strict set of rules for checking and applying offers:

1. **Code Ingestion**: Rider submits a `code` for a ride.
2. **Stateless Lookup**: Fetch the `is_active=True` and non-expired `Offer` record from the database.
3. **Eligibility Engine (Validation)**:
- **Usage Check**: `total_usage_count < usage_limit`.
- **User Lock**: `OfferUsage.objects.filter(user, offer).count() < per_user_limit`.
- **Min Fare**: `ride_value >= min_ride_value`.
- **Geofence**: Compare the ride's `city` with the offer's `city` targeting.
4. **Discount Calculation**:
- **FLAT**: `discount = min(value, ride_value)`.
- **PERCENTAGE**: `raw_discount = (ride_value * (value / 100))`. 
- **CAPPING**: `discount = min(raw_discount, max_discount)`.
5. **Application**: 
- The calculated `discount` is attached to the ride.
- **Post-Ride Commit**: Mark the `OfferUsage` record as fixed after the ride is completed.

## How Multi-Incentive Collisions are Handled

The system can be configured to either:
- **Exclude**: Only one offer can be applied per ride (First-applied takes priority).
- **Combine**: Multiple offers can be applied if their type is different (e.g. 10% off plus ₹50.00 flat). This is controlled by a system-wide flag.

## The User Experience (Rider Feedback)

While of a ride booking:
- **Validation Alert**: If the code is invalid (expired, wrong city, etc.), an error message is immediately returned to the app.
- **Applied Banner**: If valid, the app shows the discount and the updated `final_fare`.

## Atomic Transactions (Reliability)

Every set of related usage updates and ledger entries is wrapped in a **Postgres Transaction** (`transaction.atomic()`). If the ride completion fails, the usage increment is also rolled back, ensuring no"Shadow Usage"occurs.

## Future Enhancements

- **User Segment Targeting**: Restricting offers to specific rider tiers (e.g."Pro"tier only).
- **Referral Loop Integration**: Automatically creating personal promo codes for users to share with friends.
