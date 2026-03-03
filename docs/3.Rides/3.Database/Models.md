# Database Models: Rides Module

The `Ride` model is the central entity for tracking all trips.

## The `Ride` Model

The `Ride` model tracks everything about a trip, from the initial search to completion.

### Location Fields

|Field|Type|Description|
|:---|:---|:---|
|`pickup_lat/lng`|`FloatField`|Latitude/Longitude for the pickup point.|
|`pickup_address`|`CharField`|Human-readable pickup location.|
|`drop_lat/lng`|`FloatField`|Latitude/Longitude for the destination.|
|`drop_address`|`CharField`|Human-readable destination location.|
|`planned_route_polyline`|`TextField`|Encoded polyline representing the initial route.|
|`planned_distance_km`|`FloatField`|Initial distance estimation from Google Maps.|
|`planned_duration_min`|`FloatField`|Initial travel time estimation.|

### Ride Status Logic

- **`SEARCHING`**: Looking for a ride.
- **`OFFERED`**: A driver has been found and an offer is pending their response.
- **`ASSIGNED`**: Driver has accepted the ride.
- **`ARRIVED`**: Driver reached the pickup point.
- **`ONGOING`**: OTP has been verified, and the trip is in progress.
- **`COMPLETED`**: Ride successfully finished (terminal).
- **`CANCELLED`**: Trip was aborted by Rider, Driver, or System (terminal).
- **`NO_SHOW`**: Rider did not show up at the pickup location.

### Fare Components

- `base_fare`: Calculated from `FareConfig` upon booking.
- `final_fare`: Authoritative final price after completion.
- `fare_breakdown`: JSON snapshot of exactly how the final price was determined (base, distance, waiting, surge, discounts).
- `waiting_seconds`: Total time (in seconds) the driver waited at the pickup point (`arrived_at` -> `otp_verified_at`).

### Audit & Guarding

- `is_fraud_flagged`: Flagged if the actual distance or waiting time is abnormally high compared to estimates.
- `candidate_driver_ids/rejected_driver_ids`: Track the matching engine's history.
- `city`: The city for which the ride was requested (default:"Chennai").

## `RideFeedback` Model

- `ride`: The trip being rated.
- `giver_role`: `RIDER` or `DRIVER`.
- `rating`: Integer from 1 to 5.
- `comment`: Optional text review.

## `ChatMessage` Model

- `ride`: The trip context for the chat.
- `sender`: User sending the message.
- `content`: Message body.
- `is_read`: Boolean read state.