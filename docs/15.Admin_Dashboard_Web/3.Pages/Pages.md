# Pages Catalogue: Admin Dashboard Web

Each page in the Admin Dashboard corresponds to a dedicated backend module or cross-cutting concern. Below is a full catalogue with purpose and key capabilities.
---

## Operations

### `Overview` (`/overview`)
The landing page for admins. Displays real-time KPI tiles:
- **Active Rides**, **Online Drivers**, **Today's Revenue**, **Pending Payouts**, **Open Support Tickets**, **Active SOS Alerts**.
- Uses REST polling every 30 seconds (or WebSocket push for SOS updates).
---

### `Live Map` (`/live-map`)
The God's Eye real-time view. All online drivers are plotted with colour-coded status markers:
- **Green**: `ONLINE` (idle).
- **Blue**: `ON_TRIP`.
- **Red Pulsing**: `SOS ACTIVE`.
Clicking a driver marker opens a right-side detail panel with full driver profile, current trip, and action buttons (Force Cancel, Block).
---

### `Rides` (`/rides`)
Paginated, filterable table of all ride records. Columns include fare, status, driver, rider, distance, and timestamps. Supports drill-down to a full ride audit page.
---

## Supply

### `Drivers` (`/drivers`)
Full driver roster with status, trust score, level, and acceptance rate. Supports status override (BLOCK/UNBLOCK) directly from the table.
---

### `Verification` (`/drivers/verification`)
Document review queue showing pending driver applications. Admins can approve or reject individual documents with a reason note, triggering automated driver status updates.
---

### `Driver Incentives` (`/driver-incentives`)
CRUD interface for incentive campaigns (`STREAK`, `PEAK`, `ZONE`). Displays active campaign stats and total payout-to-date per campaign.
---

## Finance

### `Payments` (`/payments`)
Full payment transaction history with gateway status, amounts, and rider details.

### `Ledger` (`/payments/ledger`)
Read-only view of every `LedgerEntry` across the platform — the immutable financial audit trail. Supports filtering by reason, type (CREDIT/DEBIT), and date range.

### `Payouts` (`/payments/payouts`)
Driver payout queue. Displays pending withdrawal requests with driver bank details. Admins can trigger individual or bulk payout processing.

### `Fare Config` (`/fare-config`)
Interface for modifying base fares, per-km rates, night surcharges, and platform commission percentage per city and vehicle type.
---

## Marketing

### `Offers` (`/offers`)
Full lifecycle management for promo codes: create, edit, activate/deactivate. Displays real-time usage counts alongside budget consumption.
---

## Platform

### `Support` (`/support`)
Unified ticket and emergency management. Two sub-tabs:
- **Tickets**: Filter by status (OPEN/RESOLVED/REJECTED) with resolve/reject actions.
- **Emergencies (SOS)**: Active alert queue with GPS snapshot and ride context for each event.

### `Alerts` (`/alerts`)
Live feed of `SystemLog` entries from the backend. Filterable by type (`ERROR`, `PAYMENT_FAILURE`, `RIDE_STUCK`).

### `Analytics` (`/analytics`)
Recharts-powered dashboards: daily ride volume, revenue breakdown, driver performance distribution, and rider retention rates.

### `Reports` (`/reports`)
Scheduled or on-demand CSV/PDF export of financial and operations data.

### `Observability` (`/observability`)
Embedded Prometheus/Grafana iframe panels for system-level metrics (CPU, DB pool, Celery queue depth, API latency P99).
