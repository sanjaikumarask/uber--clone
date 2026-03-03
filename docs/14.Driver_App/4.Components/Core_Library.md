# Core Component Library: Driver App

The Driver App component library is purpose-built for a high-stakes, eyes-partially-on-road usage context. Every element prioritises legibility, large touch targets, and minimal cognitive load.

## The Component Principles

1. **High Contrast**: Dark backgrounds with vibrant accent colours so components are readable in direct sunlight from a dashboard mount.
2. **Large Touch Targets**: All interactive elements follow a minimum 48 dp touch target as per Android/iOS accessibility guidelines, crucial for use while the vehicle is stationary.
3. **Audio-First Alerts**: Any critical state change (new ride offer, rider cancellation) is paired with an audio cue so the driver does not need to look at the screen immediately.

## The Core UI Library

### 1. `MapComponents`
- **`DriverMap`**: Full-screen map centered on the driver's position, auto-rotating to match `heading`.
- **`PickupMarker` / `DropoffMarker`**: Distinctive coloured pins for the two navigation waypoints.
- **`RoutePolyline`**: Decoded polyline of the planned path rendered as a bold, easily-visible blue line.

### 2. `ShiftComponents`
- **`OnlineToggle`**: Large two-state switch at the center of the Home screen that starts/stops GPS broadcast and changes status.
- **`EarningsCard`**: A compact summary tile showing today's gross, trips count, and acceptance rate.
- **`StatusBadge`**: Colour-coded badge (Green/Red/Yellow) indicating `ONLINE`, `OFFLINE`, or `ON_TRIP`.

### 3. `RideOfferSheet`
- **`RideOfferCard`**: Full-screen interrupt modal that appears when a new ride is dispatched. Shows rider name, pickup distance, estimated earnings, and a 15-second countdown timer with Accept / Reject actions.
- **`OTPVerificationPanel`**: Prominent display for the 4-digit OTP the driver must confirm with the rider before starting the trip.

### 4. `FinanceComponents`
- **`WalletBalanceCard`**: Shows current ledger balance with a direct"Withdraw"button.
- **`EarningsBreakdown`**: Itemised list of fares with deductions and net payout per trip.
- **`IncentiveProgressBar`**: Visual streak tracker (e.g.,"3 / 5 rides completed for ₹500 bonus").
