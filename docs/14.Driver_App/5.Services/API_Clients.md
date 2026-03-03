# Services & Background Systems: Driver App

The Driver App relies on several concurrent services that operate independently — some in the foreground, others as persistent background tasks — to maintain reliable communication with the backend.

## The Service Principles

1. **Background Resilience**: The GPS broadcast service must survive screen locks and app backgrounding on both iOS and Android.
2. **Fail-Safe Delivery**: API calls use exponential backoff retry so transient network drops during a trip do not result in lost location events.
3. **Encapsulated Business Logic**: All interaction with the backend is wrapped in typed service modules, keeping screen components focused purely on UI.

## The Core Services

### 1. `AuthService`
- **Responsibility**: Driver registration, login, JWT refresh, and logout.
- **Key Methods**: `login(phone, password)`, `refreshToken()`, `getProfile()`.

### 2. `RideService`
- **Responsibility**: Accepting/rejecting ride offers, marking arrival, starting, and completing trips.
- **Key Methods**: `acceptRide(rideId)`, `rejectRide(rideId)`, `markArrived(rideId)`, `startRide(rideId, otp)`, `completeRide(rideId)`.

### 3. `LocationBroadcastService` (`expo-location`)
- **Responsibility**: High-frequency GPS ping transmission to `/api/tracking/location/`.
- **Behaviour**: 
- Runs every **5 seconds** while `isOnline`.
- Drops to **15 seconds** after 2 minutes of zero movement (battery saving).
- Automatically resumes 5-second frequency when movement is detected.

### 4. `RideOfferWebSocketService` (Django Channels)
- **Responsibility**: Maintains a persistent WebSocket connection for receiving ride dispatch offers from the backend.
- **Channels**: Subscribes to `driver_{id}` group.
- **On Message**: Triggers audio alert via `AudioService` and updates `useRideStore` with offer data.

### 5. `AudioService` (`expo-av`)
- **Responsibility**: Pre-loads and plays distinct sound effects for new offers, cancellations, and payment confirmations.
- **Sounds**: `new_ride.mp3`, `cancelled.mp3`, `earnings_received.mp3` loaded into memory on app launch.

### 6. `DocumentUploadService` (`expo-image-picker`)
- **Responsibility**: Handles image selection, EXIF data stripping, and chunked multipart upload to `/api/drivers/documents/`.

### 7. `WalletService`
- **Responsibility**: Fetching ledger balance, transaction history, and initiating payout requests.
- **Key Methods**: `getBalance()`, `getTransactions()`, `requestPayout(amount)`.
