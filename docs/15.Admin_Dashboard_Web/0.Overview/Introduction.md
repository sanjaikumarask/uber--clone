# Introduction to the Admin Dashboard Web

The Admin Dashboard Web is the internal, restricted-access operations portal for the Uber Clone platform. It is not exposed to riders or drivers — it is purely an ops and engineering tool.

## Global Objectives

1. **Operational Awareness**: Give platform operators a live, comprehensive view of all ongoing activity — rides, drivers, and system health — in a single browser tab.
2. **Financial Control**: Full read/write access to the payment ledger, payout queue, and refund initiation so the support and finance teams can resolve issues independently.
3. **Supply Management**: Driver verification queue and incentive/offer management to shape marketplace supply and demand.
4. **Observability Integration**: Embedded metrics dashboards and alert firehose so the engineering team can diagnose incidents without switching tools.

## Technical Stack

|Concern|Technology|
|:---|:---|
|Framework|React 19 + Vite 8|
|Language|TypeScript|
|Routing|React Router 7|
|Maps|`@react-google-maps/api`|
|Charts|Recharts|
|HTTP|Axios with JWT interceptors|
|Real-time|Native WebSocket (Django Channels)|

## Persona & Access

The Admin Dashboard is accessible only to users with `role: admin` on the backend. Attempting to access any route with a rider or driver JWT returns a `403 Forbidden` response and the UI redirects to the login page.

Key admin personas:
- **Operations Manager**: Uses Live Map, Rides, and Support pages.
- **Finance Team**: Uses Payments, Ledger, and Payouts pages.
- **Driver Relations**: Uses Drivers, Verification, and Incentives pages.
- **Engineering**: Uses Observability and Alerts pages.
