# Core Component Library: Admin Dashboard Web

The Admin Dashboard component library is built for information density, fast scanning, and actionable controls — the opposite philosophy to the consumer-facing apps.

## The Component Principles

1. **Data First**: Tables, charts, and lists dominate layouts. Every component is designed to present as much relevant information as possible at a glance.
2. **Destructive-Action Safety**: Actions like Block Driver or Trigger Refund always show a confirmation modal before proceeding.
3. **Consistent Status Colours**: A unified colour system is used across all pages — Green (`success`), Red (`error`), Yellow (`warning`), Grey (`info`) — so operators can scan status visually without reading text.

## Shared Components

### Layout
- **`AdminLayout`**: Root layout with persistent sidebar and top navbar.
- **`Sidebar`**: Grouped navigation links with active-state highlighting.
- **`PageHeader`**: Consistent `<h1>` + description + optional action button for every page.

### Data Display
- **`DataTable`**: Virtualised, sortable, filterable table with server-side pagination. The backbone of Rides, Drivers, Payments, and Ledger pages.
- **`StatCard`**: KPI tile used on the Overview page (value, label, trend delta, colour).
- **`StatusBadge`**: Colour-coded pill used everywhere — ride status, driver level, ticket status.
- **`EmptyState`**: Consistent illustration + message for zero-result filters.
- **`LoadingSpinner` / `Skeleton`**: Consistent loading states to signal data is in flight.

### Map
- **`AdminLiveMap`**: `@react-google-maps/api` wrapper with custom `DriverMarker`, `RidePolyline`, and `SOSAlert` overlay.
- **`DriverDetailPanel`**: Right-side slide-in panel when a driver marker is clicked.

### Charts (Recharts)
- **`RevenueLineChart`**: Smoothed area chart for daily/weekly/monthly revenue.
- **`RideVolumeBarChart`**: Grouped bar chart comparing booked vs completed vs cancelled.
- **`TrustScoreHistogram`**: Distribution chart of driver trust scores.

### Actions
- **`ActionMenu`**: Contextual kebab (⋮) dropdown attached to table rows with role-gated actions.
- **`ConfirmModal`**: Reusable destructive-action confirmation dialog.
- **`FilterBar`**: Composable horizontal filter strip (date range, status multi-select, city select).
- **`ExportButton`**: Triggers CSV/PDF generation calls and download.
