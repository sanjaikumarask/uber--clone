# System Design: Admin Dashboard Web Architecture

The Admin Dashboard is designed for high information density and real-time synchronisation with the backend platform.

## Component Overview

|Layer|Technology|Responsibility|
|:---|:---|:---|
|Bundler|Vite 8|Sub-second HMR dev server, optimised production builds|
|Routing|React Router 7|Declarative page routing, `<Outlet>` layouts|
|State|React Context + `useState`|Per-page local state; no global store needed for admin|
|HTTP|Axios|JWT-intercepted REST calls to the Django backend|
|Real-time|`WebSocket` (native)|Live Map driver positions, SOS alerts, system logs|
|Maps|`@react-google-maps/api`|Interactive map with custom markers and polylines|
|Charts|Recharts|Revenue, ride volume, driver performance visualisations|

## Data Flow: Live Map Firehose

1. Admin opens `LiveMap` page — WebSocket connection is established to `wss://api/ws/admin_live_map/`.
2. Backend streams `driver.location.update` events for every online driver.
3. The frontend maintains an in-memory `Map<driverId, DriverState>` updated on every event.
4. React re-renders only the affected `DriverMarker` component via a keyed list pattern.
5. SOS events (`emergency.sos.alert`) trigger a high-visibility red modal that persists until manually dismissed.

