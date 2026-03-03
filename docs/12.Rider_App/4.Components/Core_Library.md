# Core Component Library: Rider App

The Rider App provides a premium, custom UI library designed specifically for high-frequency map interactions and ride booking workflows.

## The Component Principles

The system follows a set of strict rules for UI components:

1. **Atomic Design**: Small, reusable UI atoms (Buttons, Inputs, Icons) combined into complex molecules (Ride Cards, Bottom Sheets).
2. **Platform Consistency**: Components are designed to look and feel native on both iOS and Android.
3. **High-Frequency Map UI**: Specialized markers and polylines optimized for moving driver icons.

## The Core UI Library

### 1. `MapComponents`
- **`RideMap`**: Central component that handles `react-native-maps` integration and marker clustering.
- **`DriverMarker`**: Custom marker with rotation and interpolation for real-time driver movement.
- **`PolylineRoute`**: Decoded path polylines with customizable colors and line widths.

### 2. `BookingComponents`
- **`RideSelector`**: Horizontal scrollable list for choosing vehicle types (UberGo, UberXL, etc.).
- **`FareEstimateCard`**: Displays the price, ETA, and promo code options.
- **`DestinationPicker`**: Search component with Google Places Autocomplete integration.

### 3. `ActionComponents`
- **`PrimaryButton / SecondaryButton`**: High-contrast buttons with custom loading states and haptic feedback.
- **`PromotionCard`**: Highlights active offers and applied discounts.
- **`SOSButton`**: High-priority safety component accessible during active rides.

## Specialized Interaction UI

- **`StatusBanner`**: Floating fixed banner showing the current ride state (e.g."Driver Arrived").
- **`OTPModal`**: Clean, secure interface for entering and verifying trip PINs.
- **`RatingBottomSheet`**: Interactive star-rating and feedback portal for completed trips.
