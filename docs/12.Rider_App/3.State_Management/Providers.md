# State Management: Providers & Hooks

The Rider App uses the **Context API** for application-wide state, providing a lightweight and high-performance alternative to Redux for real-time mobile applications.

## The State Principles

The system follows a set of strict rules for state updates:

1. **Single Source of Truth**: Core domains (`Auth`, `Ride`, `Location`) are managed in centralized Context Providers.
2. **Stateless UI Components**: Screens consume state and dispatch actions via custom hooks, keeping the UI components focused on rendering.
3. **Real-time Reactivity**: The `RideContext` is designed to handle high-frequency WebSocket updates (5-10 second intervals) without impacting battery life or UI smoothness.

## The Core Context Providers

### 1. `AuthContext`
- **Responsibility**: JWT persistence, User profile data, and Login/Logout logic.
- **Persistence**: Uses `@react-native-async-storage/async-storage` for cross-session token storage.

### 2. `RideContext`
- **Responsibility**: Current ride status, Assigned Driver metadata, OTP, and Route coordinates.
- **Lifecycle**: initialized on ride booking, updated via WebSockets, and cleared on ride completion or cancellation.

### 3. `LocationContext`
- **Responsibility**: Real-time user position (`lat`, `lng`) and geofencing.
- **Technology**: Integrated with `expo-location` and high-accuracy GPS permissions.

## Custom Hooks Library

Screens interact with the state through specialized hooks:
- `useAuth()`: Access current user role and session.
- `useRide()`: Get live status and tracking data for the active trip.
- `useTracking(rideId)`: Specialized hook that handles WebSocket subscription and coordinate smoothing logic.
- `useDestination()`: Manage temporary pickup/dropoff selections during the booking flow.
