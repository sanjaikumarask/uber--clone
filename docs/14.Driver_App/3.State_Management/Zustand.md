# State Management: Zustand Stores (Driver App)

The Driver App uses **Zustand** for lightweight, centralized, and high-performance global state management, perfectly suited for a real-time application with frequent background GPS updates.

## The State Principles

1. **Single Source of Truth**: Core domains (`Auth`, `Shift`, `ActiveRide`) are managed in separate, composable Zustand stores.
2. **Background-Safe Updates**: The Location store is updated by a background process and must not trigger unnecessary UI re-renders in screen components.
3. **Persistence**: Auth tokens and driver profile data are persisted across sessions using Zustand's `persist` middleware backed by `AsyncStorage`.

## The Core Zustand Stores

### 1. `useAuthStore`
- **Responsibility**: JWT token storage, driver profile (`name`, `vehicle`, `status`), and Login/Logout logic.
- **Persistence**: Synced to `@react-native-async-storage/async-storage` so the driver stays logged in across app restarts.
- **Key State**: `isAuthenticated`, `driver`, `token`.

### 2. `useShiftStore`
- **Responsibility**: Tracks and toggles the driver's `ONLINE` / `OFFLINE` status and the current GPS coordinate being broadcast.
- **Key State**: `isOnline`, `currentLat`, `currentLng`, `heading`.

### 3. `useRideStore`
- **Responsibility**: The full lifecycle of the active or offered ride, from the initial dispatch offer through to completion.
- **Lifecycle**: Created on ride offer receipt, updated at each status change (`ACCEPTED` → `ARRIVED` → `STARTED` → `COMPLETED`), and cleared on terminal states.
- **Key State**: `ride`, `riderInfo`, `offerExpiry`, `otp`.

## Custom Hooks

Screens interact with state via focused hooks:
- `useDriver()`: Returns current driver profile and online/offline toggle action.
- `useActiveRide()`: Returns ride metadata and helpers like `acceptRide()`, `markArrived()`, `startRide()`, `completeRide()`.
- `useGpsTracker()`: Encapsulates `expo-location` fencing and broadcasts to the backend.
