# System Design: Rider Web Architecture

The Rider Web application is architected for maximum performance and a reliable state synchronization with the backend.

## Component Overview

1. **React Router Stack**: Handles declarative navigation and layout management, ensuring a robust and performant screen hierarchy.
2. **Global Store (Zustand)**: Used for managing `Auth`, `Ride`, and `Location` state throughout the app without the boilerplate of Redux.
3. **API Services**: Axios-based clients with interceptors for JWT token handling and error management.
4. **WebSocket Manager**: Centralized handler for `ride_{id}` channel subscriptions and real-time event processing.
5. **Geo-Services**: Integrated Google Places and Maps APIs for accurate user positioning and reverse geocoding.
6. **Charts & Viz**: custom components optimized for spending trends and ride history visualization using Recharts.

## Data Flow: Live Ride Sync

1. **Subscription**: Upon ride assignment, the app subscribes to the `ride_{id}` WebSocket group.
2. **Ingestion**: `location.update` events arrive via the WebSocket manager.
3. **State Update**: The data is pushed into the Zustand `rideStore`.
4. **UI Feedback**:
- **Marker Rotation**: The driver icon's `heading` is updated.
- **Interpolation**: Smooth movement of the driver icon using native CSS transitions or simple JS-based interpolation.
- **Polyline**: The `planned_route_polyline` is decoded and rendered on the map.

## Pages & Components

- **Home**: The landing page for destination search and recent ride history.
- **BookRide**: Fare estimates, vehicle type selection, and payment/offer configuration.
- **RideSearching**: Animated waiting screen with real-time cancel options.
- **RideTracking**: The active trip view with live driver position, ETA, and SOS button.
- **RideCompleted**: Final fare breakdown, tip options, and driver rating portal.
- **AdminDashboard**: A specialized view within the rider portal for viewing high-level stats (linked for convenience).
