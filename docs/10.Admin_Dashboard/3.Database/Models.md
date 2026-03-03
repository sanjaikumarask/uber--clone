# Database Models: Admin Dashboard Module

The Admin Dashboard relies on a specialized model for system-wide auditing and real-time failure alerting.

## The `SystemLog` Model (Audit Trail)

The root transactional entity representing a single platform alert.

### Key Fields
- `type`: `ERROR`, `WARNING`, `INFO`, `PAYMENT_FAILURE`, `RIDE_STUCK`, `WS_DISCONNECT`.
- `message`: A human-readable summary of the event (e.g."Payment ID 42 Failed: Gateway Declined").
- `metadata`: A JSONField for any specific correlation IDs (e.g. `ride_id`, `driver_id`, `error_stack`).
- **`created_at`**: Important for monitoring the"Freshness"of an alert.

## Platform State Models (Aggregates)

While many summaries are calculated on the fly, the dashboard provides a unified view of state from across the platform:
- **Users & Drivers**: Statistics pulled from the [**Users**](../../1.Users_Authentication/3.Database/Models.md) and [**Drivers**](../../2.Drivers/3.Database/Models.md) models.
- **Revenue & Ledger**: Real-time sums pulled from the [**Payments ledger**](../../4.Payments/3.Database/Models.md).
- **Safety Alerts**: Snapshot of any `ACTIVE` records on the [**Support Emergency**](../../9.Support/3.Database/Models.md) model.

## Atomic Transitions (Database Integrity)

System alerts are inserted by background logic from every module. By using a specialized `SystemLog` model, we ensure that technical failure information is separate from business-critical data (like ride fares or driver locations), preventing sensitive technical alerts from clogging the core transactional tables.
