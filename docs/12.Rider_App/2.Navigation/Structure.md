# Navigation Structure: Rider App

The Rider App utilizes React Navigation 7 for a robust and performant screen hierarchy, supporting deep linking and complex conditional navigation flows.

## Component Overview

1. **Auth Stack**: Handles `Login` and `Signup` screens.
2. **App Drawer**: A custom side drawer for `Profile`, `Ride History`, `Offers`, and `Support`.
3. **App Home Stack**: The core booking and ride flow hierarchy.
4. **Tracking & Completion**: Specialized screens for active and finished trips.

## The Navigation Flow

### 1. Root Navigator (Switcher)
- **If Authenticated**: Loads the **App Navigator**.
- **If Not Authenticated**: Loads the **Auth Stack**.

### 2. The Auth Stack
- `Login`: Phone/Email entrance and JWT acquisition.
- `Signup`: Onboarding for new riders.

### 3. The App Stack (Core Flow)
- `Home`: Main map view and destination search bar.
- `DestinationSearch`: Full-screen autocomplete for ride pickup and dropoff.
- `ConfirmRide`: Fare estimates, promo codes, and ride type selection.
- `RideSearching`: Animated waiting screen with real-time cancel options.
- `RideTracking`: Active trip map with live driver position and ETA.
- `RideCompletion`: Trip summary, rating, and payment finalization.
- `SupportScreen / CreateSupport`: Issue reporting and dispute management.
- `OffersScreen`: Browse active promotional codes and bonuses.

## Conditional Navigation Logic

The system implements strict rules for navigation during active rides:
- **Locking**: If a user is on an active ride (`ASSIGNED` or `ONGOING`), the app can"lock"them into the `RideTracking` screen until the trip is completed or cancelled.
- **Redirects**: Upon app backgrounding and re-opening, the root navigator checks for the most recent active ride state and redirects accordingly.
