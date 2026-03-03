# API Clients & Specialized Services

The Rider App uses centralized services for backend communication, real-time signaling, and location management, providing a robust interface for data ingestion and synchronization.

## The Service Principles

The system follows a set of strict rules for backend and external API interaction:

1. **Axios Client with Interceptors**: All REST calls are routed through a base Axios client that handles JWT token injection and 401/403 error redirects.
2. **Stateless WebSocket Handlers**: WebSocket messages are processed by a dedicated service that manages `ride_{id}` subscriptions.
3. **Encapsulated Logic**: Business logic is separated from UI components, with services handling data fetching and state transformation.

## The Core Services

### 1. `AuthService`
- **Responsibility**: Login, Signup, OTP Verification, and Token Persistence.
- **Method**: `login(phone, password)`, `register(userData)`, `logout()`.

### 2. `RideService`
- **Responsibility**: Ride booking, Fare estimation, Driver assignment monitoring, and Cancellation.
- **Method**: `bookRide(rideData)`, `getRideStatus(id)`, `cancelRide(id)`.

### 3. `TrackingService` (WebSocket)
- **Responsibility**: Real-time position updates for the active trip.
- **Channels**: Subscribes to `ride_{id}` and `location.update` events.

### 4. `PaymentService` (Razorpay)
- **Responsibility**: Secure payment creation and capture.
- **Method**: `initiatePayment(amount)`, `capturePayment(orderId)`.

### 5. `LocationService` (Expo Location)
- **Responsibility**: Real-time user positioning and geocoding.
- **Method**: `getCurrentLocation()`, `watchPositionAsync()`.

## Specialized External APIs

- **Google Roads/Maps API**: Used for route polyline fetching and snap-to-road calculations.
- **Expo Notifications**: Centralized push notification service integration for ride alerts.
- **Twilio / SendGrid**: Optional direct integration for SMS/Email receipts and updates.
