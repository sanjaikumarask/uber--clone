# API Clients & Web Services

The Rider Web application uses centralized services for backend communication, real-time signaling, and location management, providing a robust interface for data ingestion and synchronization on the browser.

## The Service Principles

The system follows a set of strict rules for backend and external API interaction:

1. **Axios Client with Interceptors**: All REST calls are routed through a base Axios client that handles JWT token injection and 401/403 error redirects.
2. **Stateless WebSocket Handlers**: WebSocket messages are processed by a dedicated service that manages `ride_{id}` subscriptions.
3. **Encapsulated Logic**: Business logic is separated from UI pages, with services handling data fetching and state transformation.

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

### 4. `PaymentService` (Standard Web)
- **Responsibility**: Secure payment creation and capture via web-standard gateways.
- **Method**: `initiatePayment(amount)`, `confirmPayment(transactionId)`.

### 5. `LocationService` (Browser Geolocation)
- **Responsibility**: User positioning and address search.
- **Method**: `getCurrentPosition()`, `searchPlaces(query)`.

## Specialized External APIs

- **Google Maps JavaScript API**: Used for interactive map rendering, markers, and polylines.
- **Google Places API**: Integrated for address autocomplete and destination search.
- **Recharts**: Integrated for historical data visualization and spending trends.
