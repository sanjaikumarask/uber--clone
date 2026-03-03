# System Design: Rider App Architecture

The Rider App is architected for maximum performance and a reliable state synchronization with the backend.

## Component Overview

1. **Navigation Stack**: Managed by React Navigation 7, ensuring a robust and performant screen hierarchy.
2. **State Management**: Context API used for managing `Auth`, `Ride`, and `Location` state throughout the app.
3. **API Services**: Axios-based clients with interceptors for JWT token handling and error management.
4. **WebSocket Manager**: Centralized handler for `ride_{id}` channel subscriptions and real-time event processing.
5. **Geo-Services**: Integrated Expo Location for accurate user positioning and reverse geocoding.
6. **Maps & Visualization**: Custom map components optimized for marker movements and path polyline rendering.

## Data Flow: Live Ride Sync

1. **Subscription**: Upon ride assignment, the app subscribes to the `ride_{id}` WebSocket group.
2. **Ingestion**: `location.update` events arrive via the WebSocket manager.
3. **State Update**: The data is pushed into the `RideContext`.
4. **UI Feedback**:
- **Marker Rotation**: The driver icon's `heading` is updated.
- **Interpolation**: Smooth movement of the driver icon using `react-native-reanimated`.
- **Polyline**: The `planned_route_polyline` is decoded and rendered on the map.

## Screens & Components

- **Home**: The map-centric landing page for destination search and recent ride history.
- **ConfirmRide**: Fare estimates, vehicle type selection, and payment/offer configuration.
- **RideSearching**: Animated waiting screen with real-time cancel options.
- **RideTracking**: The active trip view with live driver position, ETA, and SOS button.
- **RideCompletion**: Final fare breakdown, tip options, and driver rating portal.
