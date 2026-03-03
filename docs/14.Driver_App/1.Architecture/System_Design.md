# System Design: Driver App Architecture

The Driver App is architected for continuous network communication and robust background processing, contrasting the more session-based nature of the Rider App.

## Component Overview

1. **Navigation Stack**: Managed by React Navigation 7, isolating the onboarding flow from the active-driving flow.
2. **Global Store (Zustand)**: Specialized stores for `AuthStore` (Tokens), `ShiftStore` (Online status, Location), and `RideStore` (Active Trip).
3. **API & WebSocket Services**: Axios configuration alongside a Django Channels WebSocket client for real-time ride offers.
4. **Location Broadcaster**: Background task manager built on `expo-location` to continuously burst `(lat, lng)` ping to the tracking server.
5. **Audio Engine**: Pre-loaded sound files triggered by state changes (e.g.,'New Ride Alert').

## Data Flow: Location Streaming

The core responsibility of the Driver App while `ONLINE` is maintaining an accurate position on the global map:
1. **Trigger**: Driver toggles switch to `ONLINE`.
2. **Location Binding**: App starts `watchPositionAsync` with high accuracy.
3. **Transmission**: Every 5-10 seconds, the frontend posts a payload `{"lat": X,"lng": Y,"heading": Z}` to `/api/tracking/location/`.
4. **Backend Integration**: The backend processes this ping (smoothing, snapping) and broadcasts it to any tracking riders and the Admin Dashboard.

## Screens & Components

- **Home**: The primary operational map where drivers toggle their status and await pings.
- **DocumentUpload**: Multi-step form for submitting ID, License, and Vehicle Registration.
- **RideOffer**: High-visibility modal that interrupts the screen with a loud sound when a ride is dispatched.
- **RideTracking**: Turn-by-turn style map view for executing an accepted ride.
- **Wallet**: Dashboard for ledger balances, earnings breakdown, and payout requests.
- **Incentives**: Tracking for gamified elements like"Complete 5 rides for ₹500".
