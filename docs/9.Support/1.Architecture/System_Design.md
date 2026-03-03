# System Design: Support Module

The architecture of the Support module is designed for both asynchronous inquiry handling and real-time emergency signaling.

## Component Overview

1. **Support API**: Public endpoints for listing history and submitting tickets, SOS alerts, and fetching FAQs.
2. **Emergency Coordinator**: High-priority service that captures a GPS snapshot and ride status at the moment of an SOS trigger.
3. **Real-time Broadcaster**: WebSocket Consumers that push SOS events and ride metadata to the **Admin Dashboard**.
4. **FAQ Store**: Multi-audience (Rider/Driver) database of self-service knowledge articles.
5. **Resolution Workflow**: Django Admin/Support interface for managing ticket status and resolution notes.

## Data Flow: Emergency (SOS) Dispatch

1. **Trigger**: User (Rider or Driver) presses the SOS button in the mobile app during a ride.
2. **Ping Capture**: The mobile app instantly POSTs its current (lat, lng) and information to the backend.
3. **Creation**: An `Emergency` record is created (`status: ACTIVE`).
4. **Real-time Broadcast**: 
- The system identifies the active ride and driver.
- An `emergency.alert` is pushed via **Django Channels** to the `admin_live_map` group.
- The Admin Dashboard instantly shows a Red Banner and a pulsing marker on the map for that ride.
5. **Audit & Resolve**: Admin reviews the situation, updates the `resolution_note`, and sets `status: RESOLVED`.
