# Navigation Structure: Rider Web Platform

The Rider Web application utilizes React Router 6 for a robust and performant screen hierarchy, supporting declarative navigation and complex conditional routing flows.

## Component Overview

1. **Auth Stack**: Handles `Login` and `Signup` pages.
2. **App Layout**: A persistent top navigation bar and side drawer for `Profile`, `Ride History`, `Offers`, and `Support`.
3. **App Core Stack**: The primary booking and ride flow hierarchy.
4. **Tracking & Completion**: Specialized pages for active and finished trips.

## The Navigation Flow

### 1. Root Router (Switcher)
- **If Authenticated**: Loads the **App Layout**.
- **If Not Authenticated**: Loads the **Auth Stack**.

### 2. The Auth Stack
- `Login`: Phone/Email entrance and JWT acquisition.
- `Signup`: Onboarding for new riders.

### 3. The App Layout (Core Flow)
- `Home`: Main map view and destination search bar.
- `BookRide`: Fare estimates, promo codes, and ride type selection.
- `RideSearching`: Animated waiting screen with real-time cancel options.
- `RideTracking`: Active trip map with live driver position and ETA.
- `RideCompleted`: Trip summary, rating, and payment finalization.
- `SupportPage / CreateTicketPage`: Issue reporting and dispute management.
- `OffersPage`: Browse active promotional codes and bonuses.
- `AdminDashboard`: Specialized dashboard within the rider portal for high-level monitoring (linked for convenience).

## Conditional Navigation Logic

The system implements strict rules for navigation during active rides:
- **Locking**: If a user is on an active ride (`ASSIGNED` or `ONGOING`), the app can"lock"them into the `RideTracking` page until the trip is completed or cancelled.
- **Redirects**: Upon page refresh or re-opening, the root router checks for the most recent active ride state and redirects accordingly.
