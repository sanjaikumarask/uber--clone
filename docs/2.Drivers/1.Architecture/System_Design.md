# System Design: Drivers Module

The architecture of the Drivers module is designed to handle high-frequency location updates and a robust multi-stage verification pipeline.

## Component Overview

1. **Driver Profile**: Core metadata (vehicle, bank info) and link to the `User` identity.
2. **Verification Pipeline**: Manages document uploads (`DriverDocument`) and approval workflows.
3. **Real-time GEO Layer**: Redis-backed subsystem that stores and queries driver coordinates.
4. **Metrics & Scoring Engine**: Aggregates ride data into `DriverStats` and calculates levels.
5. **Admin Operator View**: Interface for manual document review and level overrides.

## Data Flow: Location & Availability

1. **Update**: Driver app POSTs updated coordinates to the API (or via WebSocket).
2. **Storage**: 
- **PostgreSQL**: `last_lat/lng` on the `Driver` model is updated for long-term tracking.
- **Redis**: `GEOADD` is called to update the driver's presence in the city-specific search index.
3. **Expiration**: If a driver's heartbeats stop, they are pruned from the Redis geo-index to prevent stale matches.

## Verification Guard (FSM Integration)

The `Driver` model implements a status guard:
- A driver **cannot** transition to `ONLINE` status unless `is_verified` is True.
- Verification requires a strict subset of documents (License, RC, Insurance) to be in `APPROVED` status.
