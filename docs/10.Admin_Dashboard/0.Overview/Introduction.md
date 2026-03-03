# Introduction to the Admin Dashboard

The Admin Dashboard is the authoritative internal application used by platform operators to monitor and manage the Uber Clone ecosystem.

## Global Objectives

1. **Operational Visibility**: Provide a"God's Eye View"of the entire platform, showing live driver positions and active ride routes.
2. **Incident Management**: Real-time alerting for system failures, stuck rides, and safety SOS triggers.
3. **Revenue Monitoring**: Automated summaries of daily transactions, platform commissions, and payout statuses.
4. **Supply Coordination**: Identify geographic areas with high rider demand and low driver supply to manage surge pricing or driver alerts.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **Real-time Layer**: Django Channels (WebSockets) for the live map firehose.
- **Frontend**: React (Separate repository) communicating via authenticated REST and WebSocket APIs.
- **Analytics**: PostgreSQL aggregations and Redis-backed real-time counters.

## The Dashboard Concept

The dashboard is divided into three primary functional areas:
- **Live Monitor**: Map-centric view of active operations (Drivers, Rides, SOS).
- **Management Portals**: CRUD interfaces for Users, Drivers, Payments, and Offers.
- **System Health**: Firehose for `SystemLog` (Alerts) to catch and fix technical issues in real-time.
