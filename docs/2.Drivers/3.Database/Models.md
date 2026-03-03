# Database Models: Drivers Module

The Drivers system relies on three primary models to manage identity, verification, and performance.

## The `Driver` Model

The root entity representing a driver partner and their vehicle.

### Key Fields
- `status`: `OFFLINE`, `ONLINE`, `BUSY`, `BLOCKED`.
- `level`: `NORMAL`, `ACTIVE`, `CONSISTENT`, `PRO`.
- `is_verified`: Boolean set only after required documents are approved.
- `vehicle_model / vehicle_number`: Basic asset tracking.
- `last_lat / last_lng`: Store the most recent coordinates for historical/cold lookup.

## `DriverDocument` Model

Tracks the multi-stage verification process for each driver.

### Types & Processing
- **Required Types**: `LICENSE`, `RC`, `INSURANCE`.
- **Optional Types**: `AADHAAR`.
- **Status**: `PENDING`, `APPROVED`, `REJECTED`.
- **Logic**: When a required document is approved, the system checks if the total set of required docs are `APPROVED` and automatically sets `Driver.is_verified = True`.

## `DriverStats` Model

A denormalized table for tracking performance metrics and reputation.

### Trust & Reputation
- **`trust_score`**: (0-100) Base reputation. Drops on cancellations or fraud flags.
- **`acceptance_rate`**: (%) Percentage of offered rides that the driver accepted.
- **`rejection_count_today`**: Used to enforce the"Auto-Assign"penalty after 3 rejections.
- **`avg_rating`**: Calculated average from rider feedback.

## `DriverLevelHistory` Model

An audit trail for level changes (e.g. `NORMAL` -> `ACTIVE`). Captures the old level, new level, time, and reason (automatic or admin override).
