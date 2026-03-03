# System Design: Rides Module

The architecture of the Rides module is designed to handle high concurrency and provide low-latency updates.

## Component Overview

The module consists of several decoupled components:

1. **Ride API**: Manages CRUD operations and state transitions.
2. **Matching Engine**: Asynchronous service that finds and provides ride offers to drivers sequentially.
3. **Fare Engine**: Logic for calculating estimated and final fares.
4. **Real-time Broadcast**: Push-based update system using WebSockets.
5. **Tracking System**: Snaps driver GPS coordinates and maintains the `actual_distance_km` count.

## Data Flow & WebSockets

The system utilizes **Django Channels** for real-time communication:

- **`ride_{id}` Group**: Notifies the Rider about status changes, OTP generation, and final fare completion.
- **`driver_{id}_rides` Group**: Sends new ride offers, cancellation alerts, and status synchronization to the Driver's app.
- **`admin_live_map` Group**: Provides a streaming firehose of all active ride events to the Admin Dashboard.

### Critical Flow: Status Update

When `update_ride_status(ride, new_status)` is called:
1. **FSM Validation**: The logical transition is verified.
2. **State Logic**: Specific effects (OTP generation, locking waiting time, clearing driver status) are executed.
3. **Durability Check**: The state is committed to the database.
4. **Triple Broadcast**: The update is pushed to Rider, Driver, and Admin simultaneously.
5. **Ledger Update**: For terminal states (`COMPLETED`, `CANCELLED`), financial records are reconciled.

## Core Storage: PostgreSQL

The `Ride` model is the central entity. It uses **JSONFields** for flexibility:
- `candidate_driver_ids`: Ordered list of drivers being considered.
- `rejected_driver_ids`: Drivers who have already declined the ride.
- `fare_breakdown`: Immutable audit log of the final fare components.

## Scalability Considerations

- **Redis GEO**: Efficient proximity searches for matching.
- **Distributed Locking**: Prevents"phantom assignments"where multiple rides are offered to the same driver.
- **Celery Workflows**: Decouples heavy operations like distance snapping and notification dispatch from the request-response cycle.