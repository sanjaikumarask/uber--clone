# Navigation Structure: Admin Dashboard Web

The Admin Dashboard uses React Router 7 for declarative, layout-driven routing. All routes live under a shared `<AdminLayout>` that renders the persistent sidebar and top navigation bar.

## Route Map

```
/login ← Public: Login page (no sidebar)
/ ← Protected: redirects to /overview
/overview ← Platform summary KPIs
/live-map ← Real-time driver & ride map (WebSocket)
/rides ← Ride history and search
/drivers ← Driver roster and status management
/drivers/verification ← Document review queue
/payments ← Payment transaction listing
/payments/ledger ← Immutable ledger audit view
/payments/payouts ← Driver payout queue and processing
/offers ← Promotional code CRUD
/driver-incentives ← Incentive campaign CRUD
/support ← Ticket and SOS alert management
/alerts ← System log firehose
/analytics ← Charts and reporting
/reports ← Exportable revenue and operations reports
/observability ← Embedded Prometheus/Grafana metrics
/fare-config ← Base fare and surge multiplier configuration
```

## Role-Based Guard

Every protected route (i.e., everything except `/login`) is wrapped in an `<AdminGuard>` component that:
1. Reads the JWT from `localStorage`.
2. Decodes the `role` claim.
3. Redirects to `/login` if the token is absent, expired, or not `admin`.

## Sidebar Structure (Grouped)

```
Operations
Overview · Live Map · Rides

Supply
Drivers · Verification · Driver Incentives

Finance
Payments · Ledger · Payouts · Fare Config

Marketing
Offers

Platform
Support · Alerts · Analytics · Reports · Observability
```
