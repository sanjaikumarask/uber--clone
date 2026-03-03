# System Design: Offers Module

The architecture of the Offers module is designed for fast, stateless validation and robust auditability of promotional discounts.

## Component Overview

1. **Offers API**: Public endpoints for listing available offers and applying promo codes to a ride.
2. **Offer Engine**: Centralized matching logic for applying discount types (`FLAT` vs `PERCENTAGE`).
3. **Eligibility Service**: High-speed validation of code validity, city targeting, and user-specific usage history.
4. **Usage Store (`OfferUsage`)**: Transactional history of every code application, linked to a specific user and ride.
5. **Admin Board**: Interface for configuring and monitoring promotional campaign performance.

## Data Flow: Offer Application

1. **Code Submission**: Rider enters a promo code (e.g., `UBERNEW50`) during ride booking.
2. **Validation Stage**:
- **Code Lookup**: Fetch the `Offer` record from the database.
- **Eligibility**: Check `is_valid_now()`, `usage_limit`, `per_user_limit`, and `city` targeting.
3. **Calculation**:
- **Flat**: Discount = `value`.
- **Percentage**: Discount = `min(ride_value * (value/100), max_discount)`.
4. **Ride Association**: 
- If valid, the discount amount is attached to the `Ride` model (`applied_offer`).
- The `final_fare` calculation logic in the [**Rides module**](../../3.Rides/4.Core_Logic/Fare_Calculation.md) incorporates the discount.
5. **Audit on Completion**: Once the ride is `COMPLETED`, the `OfferUsage` record is created to track the final discount and the `total_usage_count` is incremented.

## Discount Calculation Logic

The system supports two primary discount models:
- **FLAT**: A fixed amount (e.g. ₹50.00 off) regardless of the ride fare.
- **PERCENTAGE**: A percentage of the ride fare (e.g. 20% off), typically with a `max_discount` cap (e.g. ₹100.00) to ensure economic stability.
