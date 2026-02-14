# Uber Driver App

React Native driver application built with Expo for the Uber clone backend.

## Features

- ✅ Driver authentication (phone + password)
- ✅ Online/Offline status toggle
- ✅ Real-time location tracking
- ✅ Ride offer acceptance/rejection
- ✅ OTP verification to start rides
- ✅ Ride status management (Assigned → Arrived → Ongoing → Completed)
- ✅ No-show marking
- ✅ WebSocket support for real-time updates

## Tech Stack

- **React Native** with Expo
- **TypeScript**
- **React Navigation** for routing
- **Zustand** for state management
- **Axios** for API calls
- **Expo Location** for GPS tracking
- **React Native Maps** for map display
- **AsyncStorage** for local storage

## Setup

### Prerequisites

- Node.js 18+
- Expo CLI
- Android Studio (for Android) or Xcode (for iOS)
- Backend running on `localhost:8000`

### Installation

```bash
cd frontend/driver-app
npm install
```

### Running the App

#### iOS Simulator (macOS only)
```bash
npm run ios
```

#### Android Emulator
```bash
npm run android
```

#### Web (for testing)
```bash
npm run web
```

#### Physical Device
```bash
npx expo start
```
Then scan the QR code with Expo Go app.

## API Endpoints Used

- `POST /api/users/driver-login/` - Driver login
- `POST /api/drivers/status/` - Update online/offline status
- `POST /api/tracking/update-location/` - Update driver location
- `GET /api/rides/{id}/` - Get ride details
- `POST /api/rides/{id}/accept/` - Accept ride offer
- `POST /api/rides/{id}/reject/` - Reject ride offer
- `POST /api/rides/{id}/arrived/` - Mark arrived at pickup
- `POST /api/rides/{id}/start/` - Start ride with OTP
- `POST /api/rides/{id}/complete/` - Complete ride
- `POST /api/rides/{id}/no-show/` - Mark rider as no-show

## Project Structure

```
src/
├── domains/
│   └── auth/
│       └── auth.store.ts       # Authentication state
├── navigation/
│   └── Root.tsx                # Navigation setup
├── screens/
│   ├── Login.tsx               # Login screen
│   ├── Home.tsx                # Driver dashboard
│   ├── RideOffer.tsx           # Accept/reject ride
│   └── RideTracking.tsx        # Active ride tracking
└── services/
    ├── api.ts                  # Axios configuration
    ├── storage.ts              # AsyncStorage wrapper
    └── socket.ts               # WebSocket manager
```

## Configuration

### Backend URL

The app automatically detects the platform and uses the correct backend URL:
- **Android Emulator**: `http://10.0.2.2:8000`
- **iOS Simulator**: `http://localhost:8000`

To change this, edit `src/services/api.ts`.

## Testing

### Create a Test Driver Account

```bash
# SSH into backend container
docker exec -it uber_backend bash

# Create driver user
python manage.py shell -c "
from apps.users.models import User
from apps.drivers.models import Driver
user = User.objects.create_user(
    username='driver1',
    phone='1234567890',
    password='driver123',
    role='driver',
    first_name='Test',
    last_name='Driver'
)
Driver.objects.create(user=user, status='OFFLINE')
print(f'Driver created: {user.phone}')
"
```

### Login Credentials
- Phone: `1234567890`
- Password: `driver123`

## Troubleshooting

### Location Permission Issues
- Make sure location permissions are granted in device settings
- For Android, enable "Location" in app permissions
- For iOS, allow "While Using the App" or "Always"

### Cannot Connect to Backend
- Ensure backend is running on port 8000
- For Android emulator, use `10.0.2.2` instead of `localhost`
- Check firewall settings

### WebSocket Connection Failed
- Verify WebSocket URL in `src/services/socket.ts`
- Check backend WebSocket routing configuration
- Ensure JWT token is valid

## License

MIT
