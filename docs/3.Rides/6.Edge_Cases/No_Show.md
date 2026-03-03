# Edge Cases: No Show

The"No Show"scenario occurs when the rider fails to meet the driver at the pickup location within a reasonable time.

## The No-Show Logic

The no-show workflow is triggered by the driver when they have reached the pickup point and cannot find the rider.

### Pre-Conditions for No-Show

The driver can only mark a rider as a no-show if:
- The current ride status is `ARRIVED`.
- The driver's current latitude/longitude is within a **200 m radius** of the intended `pickup_lat/lng`.
- At least **5 minutes** have passed since the driver clicked"I have arrived."

## The No-Show Workflow

This workflow is triggered via `POST /api/rides/<id>/no-show/`.

1. **FSM Transition**: `ARRIVED` -> `NO_SHOW`.
2. **Driver Availability**: The driver's status is reset to `ONLINE`.
3. **Financial Penalty**:
- A **No-Show Fee** (e.g., ₹50.00) is debited from the rider's account.
- A **No-Show Payout** (e.g., ₹40.00) is credited to the driver to compensate for their time and fuel.
4. **Broadcast**:
- **Rider**: Receives a notification:"You have been marked as a no-show for your ride. A fee has been applied."
- **Driver**: Receives a notification:"Trip #XXX marked as a no-show. You have received a payout for your time."

## Admin Oversight

Admins can review all no-show events via the **Support Dashboard**. If a rider disputes a no-show, the admin can check:
1. The driver's GPS coordinates at the time of the no-show.
2. The time that the driver spent at the pickup point (`no_show_marked_at` - `arrived_at`).
3. The chat history between the rider and driver.
