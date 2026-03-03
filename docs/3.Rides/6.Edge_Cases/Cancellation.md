# Edge Cases: Ride Cancellation

The ride cancellation workflow is a robust system that handles both Rider and Driver cancellations, applying appropriate fees and penalties.

## The Cancellation Logic

The cancellation workflow is triggered via `PATCH /api/rides/<id>/cancel/`.

### Rider Cancellation (Fee-Based)

Riders can cancel a ride, but fees are applied based on the current state:

- **State: `SEARCHING` / `OFFERED`**: **FREE** cancellation ($0.00).
- **State: `ASSIGNED`**: A small cancellation fee (e.g., ₹25.00) is applied to the rider's account.
- **State: `ARRIVED`**: A higher cancellation fee (e.g., ₹50.00) is applied.
- **State: `ONGOING`**: Cancellation is **REJECTED**; the ride must be completed.

### Driver Cancellation (Penalty-Based)

Drivers can cancel an assigned ride, but it carries a penalty:

- **Trust Score Penalty**: The driver's trust score is reduced (e.g., -5 points).
- **Blocked Period**: The driver is temporarily blocked from receiving new offers (e.g., 5-minute cooldown).
- **FSM Transition**: `ASSIGNED` -> `CANCELLED`.
- The system immediately re-triggers the matching engine for the rider as a high-priority request.

## The Broadcast Flow

Upon cancellation:
1. **Notification**: A `RIDE_CANCELLED` push notification is sent to the other party.
2. **WebSocket**: Both Rider and Driver apps receive a cancellation update to clear their screens.
3. **Payment**: If a fee is due, a `Payment` record (status: `CAPTURED`) is created, and the Rider's balance is debited.

## Admin Action: System Cancellation

If a ride is stuck in `SEARCHING` or `OFFERED` state for too long (e.g., 5+ minutes):
- The **Auto-Resolve Stuck Rides** background task triggers.
- `cancelled_by`: `SYSTEM`.
- The rider is notified:"Sorry, no drivers found. Please try again later."
- The ride record is moved to the history with zero fare.

