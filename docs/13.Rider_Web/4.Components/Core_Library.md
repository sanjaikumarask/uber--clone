# Core Component Library: Rider Web

The Rider Web application provides a premium, custom UI library designed specifically for high-frequency map interactions and ride booking workflows on the browser.

## The Component Principles

The system follows a set of strict rules for UI components:

1. **Atomic Design**: Small, reusable UI atoms (Buttons, Inputs, Icons) combined into complex molecules (Ride Cards, Bottom Sheets).
2. **Platform Consistency**: Components are designed to look and feel premium and consistent with the platform's dark-mode aesthetic.
3. **High-Frequency Map UI**: Specialized markers and polylines optimized for moving driver icons using the Google Maps API.

## The Core UI Library

### 1. `MapComponents`
- **`LiveMap`**: Central component that handles `@react-google-maps/api` integration.
- **`DriverMarker`**: Custom marker with rotation and interpolation for real-time driver movement.
- **`PolylineRoute`**: Decoded path polylines with customizable colors and line widths.

### 2. `BookingComponents`
- **`RideSelector`**: Horizontal scrollable list for choosing vehicle types (UberGo, UberXL, etc.).
- **`FareEstimatePanel`**: Displays the price, ETA, and promo code options in a clean side-panel.
- **`DestinationSearch`**: Search component with Google Places Autocomplete integration.

### 3. `ActionComponents`
- **`PrimaryButton / SecondaryButton`**: High-contrast buttons with custom loading states and hover effects.
- **`PromotionCard`**: Highlights active offers and applied discounts.
- **`SOSButton`**: High-priority safety component accessible during active rides.

## Specialized Interaction UI

- **`StatusBanner`**: Floating fixed header showing the current ride state (e.g."Driver Arrived").
- **`OTPDisplay`**: Clean, secure interface for displaying and verifying trip PINs.
- **`RatingModal`**: Interactive star-rating and feedback portal for completed trips.
- **`AnalyticsCharts`**: Interactive charts for ride history and spending trends using Recharts.
