# Testing Uber Clone on Your Mobile Device

## Complete Setup Guide

### Prerequisites
1. **Install Expo Go** on your mobile device:
   - Android: [Google Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent)
   - iOS: [App Store](https://apps.apple.com/app/expo-go/id982107779)

2. **Ensure your phone and laptop are on the same WiFi network**

---

## Step 1: Find Your Computer's Local IP Address

### On Linux (Ubuntu):
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```
Or simpler:
```bash
hostname -I | awk '{print $1}'
```

### On macOS:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### On Windows:
```bash
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter.

**Example IP:** `192.168.1.100` (yours will be different)

---

## Step 2: Update Backend Configuration

### 2.1 Update Django Settings
Edit `/home/sanjai/dev/uber-backend/backend/config/settings.py`:

```python
# Find ALLOWED_HOSTS and update it:
ALLOWED_HOSTS = ["*"]  # Already set

# Find CORS_ALLOWED_ORIGINS and add your IP:
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://192.168.1.100:8000",  # Replace with YOUR IP
    "http://192.168.1.100:19000", # Expo dev server
    "http://192.168.1.100:19001", # Expo dev server
]

# Find CSRF_TRUSTED_ORIGINS and add your IP:
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://192.168.1.100:8000",  # Replace with YOUR IP
]
```

### 2.2 Update Docker Compose (if needed)
Edit `/home/sanjai/dev/uber-backend/docker-compose.yml`:

Find the `backend` service and ensure ports are exposed:
```yaml
backend:
  ports:
    - "8000:8000"
```

---

## Step 3: Update Driver App Configuration

Edit `/home/sanjai/dev/uber-backend/frontend/driver-app/src/services/api.ts`:

```typescript
import axios from "axios";
import { Storage } from "./storage";
import { Platform } from "react-native";

// REPLACE THIS IP WITH YOUR COMPUTER'S IP
const YOUR_COMPUTER_IP = "192.168.1.100"; // ← CHANGE THIS!

const HOST = Platform.OS === "android" 
  ? YOUR_COMPUTER_IP  // For physical Android device
  : YOUR_COMPUTER_IP; // For physical iOS device

export const API_URL = `http://${HOST}:8000/api`;
export const WS_URL = `ws://${HOST}:8000/ws`;

// Rest of the file remains the same...
```

---

## Step 4: Create a Test Driver Account

```bash
# SSH into backend container
docker exec -it uber_backend bash

# Run Django shell
python manage.py shell

# Create driver account
from apps.users.models import User
from apps.drivers.models import Driver

user = User.objects.create_user(
    username='9876543210',
    phone='9876543210',
    password='driver123',
    role='driver',
    first_name='Test',
    last_name='Driver'
)

driver = Driver.objects.create(
    user=user, 
    status='OFFLINE',
    last_lat=12.9716,
    last_lng=77.5946
)

print(f'✅ Driver created: {user.phone}')
exit()
```

**Login Credentials:**
- Phone: `1234567890`
- Password: `driver123`

---

## Step 5: Start the Driver App

```bash
cd /home/sanjai/dev/uber-backend/frontend/driver-app

# Start Expo development server
npx expo start
```

You'll see output like:
```
› Metro waiting on exp://192.168.1.100:8081
› Scan the QR code above with Expo Go (Android) or the Camera app (iOS)
```

---

## Step 6: Connect Your Phone

### Method 1: Scan QR Code (Recommended)
1. Open **Expo Go** app on your phone
2. Tap **"Scan QR code"**
3. Scan the QR code from your terminal
4. App will load on your device

### Method 2: Manual Connection
1. Open **Expo Go** app
2. Make sure you're on the same WiFi
3. The app should appear under "Recently opened"
4. Tap to open

---

## Step 7: Test the Complete Flow

### On Driver App (Mobile):
1. **Login** with phone `1234567890` and password `driver123`
2. **Toggle Online** - Switch status to ONLINE
3. **Wait for ride requests** (you'll create one from rider web)

### On Rider Web App (Browser):
1. Open `http://localhost:5173`
2. **Login** with phone `9876543210` and password `securepassword123` (or register new)
3. **Book a ride** from the home screen
4. **Confirm request**

### Back to Driver App:
1. You should see a **ride offer notification** (if WebSocket is working)
2. Or navigate to see the ride manually
3. **Accept the ride**
4. **Mark as Arrived**
5. **Enter OTP** (you'll see it in rider app)
6. **Start Ride**
7. **Complete Ride**

---

## Troubleshooting

### ❌ "Network request failed"
**Problem:** App can't reach backend

**Solutions:**
1. Verify your computer's IP address is correct
2. Check both devices are on same WiFi
3. Disable firewall temporarily:
   ```bash
   sudo ufw disable  # Ubuntu
   ```
4. Test backend is accessible:
   ```bash
   # On your phone's browser, visit:
   http://192.168.1.100:8000/api/users/login/
   # Should show "Method not allowed" or similar
   ```

### ❌ "Unable to connect to Expo"
**Problem:** Expo dev server not reachable

**Solutions:**
1. Make sure Expo is running: `npx expo start`
2. Try tunnel mode: `npx expo start --tunnel`
3. Restart Expo Go app

### ❌ "CORS error"
**Problem:** Backend rejecting requests

**Solutions:**
1. Add your IP to `CORS_ALLOWED_ORIGINS` in `settings.py`
2. Restart backend: `docker restart uber_backend`

### ❌ WebSocket not connecting
**Problem:** Real-time updates not working

**Solutions:**
1. Check WS_URL in `api.ts` uses `ws://` not `wss://`
2. Verify backend WebSocket routing is configured
3. For now, use polling instead (refresh manually)

---

## Quick Commands Reference

### Start Everything:
```bash
# Terminal 1: Backend (if not running)
cd /home/sanjai/dev/uber-backend
docker-compose up

# Terminal 2: Rider Web
cd /home/sanjai/dev/uber-backend/frontend/rider-web
npm run dev

# Terminal 3: Driver App
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npx expo start
```

### Check Backend Logs:
```bash
docker logs -f uber_backend
```

### Restart Backend:
```bash
docker restart uber_backend
```

---

## Testing Checklist

- [ ] Driver can login
- [ ] Driver can go online/offline
- [ ] Location updates are sent (check backend logs)
- [ ] Rider can book a ride
- [ ] Driver receives ride offer
- [ ] Driver can accept ride
- [ ] Driver can mark arrived
- [ ] OTP verification works
- [ ] Driver can start ride
- [ ] Driver can complete ride

---

## Alternative: Test on Android Emulator

If you don't have a physical device:

```bash
# Start Android emulator first
# Then run:
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npm run android
```

The emulator will use `10.0.2.2` to access your localhost automatically.

---

## Need Help?

### View Backend API:
```bash
# Test driver login endpoint
curl -X POST http://localhost:8000/api/users/driver-login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","password":"driver123"}'
```

### Check Driver Status:
```bash
docker exec -it uber_backend python manage.py shell -c "
from apps.drivers.models import Driver
d = Driver.objects.first()
print(f'Driver: {d.user.phone}, Status: {d.status}')
"
```

---

## Summary

1. **Find your IP**: `hostname -I`
2. **Update `api.ts`**: Replace `YOUR_COMPUTER_IP` with your actual IP
3. **Create driver account**: Use Django shell commands above (or use existing: `1234567890`)
4. **Start Expo**: `npx expo start`
5. **Scan QR code**: Use Expo Go app
6. **Login and test**: Phone `1234567890`, Password `driver123`

**That's it!** You should now be able to test the complete driver app on your mobile device. 🚀
