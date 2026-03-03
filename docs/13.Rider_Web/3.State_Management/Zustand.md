# State Management: Zustand Stores

The Rider Web application uses **Zustand** for lightweight, centralized, and high-performance global state management.

## The State Principles

The system follows a set of strict rules for state updates:

1. **Single Source of Truth**: Core domains (`Auth`, `Ride`, `Location`) are managed in centralized Zustand stores.
2. **Stateless UI Pages**: Components consume state and dispatch actions via custom hooks, keeping the UI components focused on rendering.
3. **Real-time Reactivity**: The `rideStore` is designed to handle high-frequency WebSocket updates (5-10 second intervals) without impacting UI smoothness.

## The Core Zustand Stores

### 1. `useAuthStore`
- **Responsibility**: JWT persistence, User profile data, and Login/Logout logic.
- **Persistence**: Uses `localStorage` for cross-session token storage via Zustand's `persist` middleware.

### 2. `useRideStore`
- **Responsibility**: Current ride status, Assigned Driver metadata, OTP, and Route coordinates.
- **Lifecycle**: Initialized on ride booking, updated via WebSockets, and cleared on ride completion or cancellation.

### 3. `useLocationStore`
- **Responsibility**: Real-time user position (`lat`, `lng`) and geofencing.
- **Technology**: Integrated with the Google Maps Places API and browser geolocation.

## Custom Selectors & Hooks

Pages interact with the state through specialized hooks:
- `useUser()`: Access current user role and session.
- `useCurrentRide()`: Get live status and tracking data for the active trip.
- `useRideTracking(rideId)`: Specialized handler that handles WebSocket subscription and coordinate smoothing logic.
- `useSearchStore()`: Manage temporary pickup/dropoff selections during the booking flow.
