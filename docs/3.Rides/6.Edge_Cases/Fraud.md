# Edge Cases: Fraud Detection

To maintain the quality and financial safety of the platform, the Rides module includes automated fraud detection mechanisms.

## The Fraud Detection Logic

Frauds are typically detected during the **Ride Completion** workflow through discrepancy analysis.

### Proximity Discrepancy

- **Trigger**: The driver marks a ride as `COMPLETED` when their current latitude/longitude is more than **1 km away** from the targeted `drop_lat/lng`.
- **Action**:
- `is_fraud_flagged = True`.
- The system sends a notification to the **Admin Dashboard Support Panel**.

### Distance-to-Estimate Gap

- **Trigger**: The `actual_distance_km` is significantly higher or lower than the intended `planned_distance_km`.
- **High Discrepancy**: > 200% of the estimate (indicates potential route manipulation).
- **Low Discrepancy**: < 50% of the estimate (indicates"ghost riding"to earn commissions).
- **Action**: Payout to the driver is delayed for 24 hours of manual auditing.

### ⏱ Waiting Time Anomalies

- **Trigger**: If `waiting_seconds` exceeds a reasonable threshold (e.g., 30 minutes) at a single point without moving the ride to `ONGOING`.
- **Action**: The ride is auto-cancelled by the system with a warning to the driver.

## The Admin Workflow

All flagged rides appear on the **Fraud Oversight Board**:
1. **Review**: Admins can see the `actual_route_polyline` compared to the `planned_route_polyline`.
2. **Correction**: Admins can manually adjust the `final_fare` to correct for driver detours.
3. **Action**: Admins can block drivers or riders found to be consistently engaging in fraudulent behavior.
