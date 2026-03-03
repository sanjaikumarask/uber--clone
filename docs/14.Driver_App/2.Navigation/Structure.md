# Navigation Structure: Driver App

The Driver App utilizes React Navigation 7 to manage a complex state-dependent navigation hierarchy. The navigation flow is strictly governed by the driver's current authentication status, verification level, and active shift state.

## The Navigation Principles

1. **Strict State Guarding**: Users are automatically routed to specific stacks based on their `DriverStatus` (e.g., Unverified drivers are locked into the Document Upload flow).
2. **Shift Persistent**: Once a driver goes `ONLINE`, the navigation bar often locks or emphasizes the live map to prevent distraction.
3. **Interruptive Alerts**: Ride offers use a modal-style"Interrupt"pattern that takes over the screen regardless of the current active tab.

## The Navigation Flow

### 1. Root Navigator (The Switcher)
- **Auth Stack**: `Login`, `Register`.
- **Onboarding Stack**: `DocumentUpload`, `VerificationPending`.
- **Main App Stack**: The core operational interface.

### 2. The Main App Stack (Tab/Drawer)
- **Home**: The primary map-based dashboard for status toggling.
- **Wallet**: Earnings, transaction history, and payout requests.
- **Incentives**: Progress tracking for streaks and bonuses.
- **Profile**: Personal details, vehicle info, and settings.
- **Notifications**: History of system and ride alerts.
- **Support**: FAQ and ticket management.

### 3. The Ride Flow (Conditional)
- **RideOffer**: High-priority modal for accepting/rejecting dispatched rides.
- **RideTracking**: Turn-by-turn style navigation screen for executing accepted rides.

## Shift-Dependent Routing

- **OFFLINE**: Driver can browse the Wallet, Incentives, and Support.
- **ONLINE**: The `Home` screen map becomes primary. Drawer/Tabs may be limited to minimize distraction.
- **ON-TRIP**: The app is locked into the `RideTracking` screen. Other navigation elements are hidden until the ride is `COMPLETED` or `CANCELLED`.

