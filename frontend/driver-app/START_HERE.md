# 🚀 Quick Start - Driver App on Mobile

## Your Configuration

**Your Computer IP:** `192.169.1.137`

**Driver Login:**
- Phone: `1234567890`
- Password: `driver123`

---

## Steps to Run

### 1. Start the Driver App
```bash
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npx expo start
```

### 2. On Your Phone
1. **Install Expo Go** from Play Store (Android) or App Store (iOS)
2. **Connect to same WiFi** as your computer
3. **Open Expo Go** app
4. **Scan the QR code** from your terminal

### 3. Login
- Phone: `1234567890`
- Password: `driver123`

---

## ✅ What's Already Configured

✅ API URL updated to `http://192.169.1.137:8000/api`  
✅ WebSocket URL updated to `ws://192.169.1.137:8000/ws`  
✅ Backend CORS configured for your IP  
✅ Backend CSRF configured for your IP  

---

## 🧪 Test the Complete Flow

### Step 1: Go Online (Driver App)
1. Login with `1234567890` / `driver123`
2. Toggle status to **ONLINE**
3. Location should start updating

### Step 2: Request Ride (Rider Web)
1. Open browser: `http://localhost:5173`
2. Login with `9876543210` / `securepassword123`
3. Click "Book Ride"
4. Confirm request

### Step 3: Accept Ride (Driver App)
1. You should see ride offer (or check manually)
2. Tap **Accept**
3. Tap **Mark as Arrived**

### Step 4: Start Ride
1. Rider will see OTP in their app
2. Enter OTP in driver app
3. Tap **Start Ride**

### Step 5: Complete Ride
1. Tap **Complete Ride**
2. Both apps should update

---

## 🔧 Troubleshooting

### ❌ "Network request failed"
```bash
# Test if backend is reachable from your phone's browser:
# Visit: http://192.169.1.137:8000/api/users/driver-login/
# Should show "Method not allowed" or similar
```

### ❌ Can't scan QR code
```bash
# Use tunnel mode instead:
npx expo start --tunnel
```

### ❌ Login fails
```bash
# Verify driver exists:
docker exec uber_backend python manage.py shell -c "
from apps.drivers.models import Driver
d = Driver.objects.get(user__phone='1234567890')
print(f'Driver: {d.user.phone}, Status: {d.status}')
"
```

---

## 📱 Alternative: Test on Emulator

### Android Emulator
```bash
# Start Android Studio emulator first, then:
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npm run android
```

### iOS Simulator (macOS only)
```bash
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npm run ios
```

---

## 🎯 Quick Commands

### Check Backend Status
```bash
docker ps | grep uber_backend
```

### View Backend Logs
```bash
docker logs -f uber_backend
```

### Restart Backend
```bash
docker restart uber_backend
```

### Check Driver Status
```bash
docker exec uber_backend python manage.py shell -c "
from apps.drivers.models import Driver
for d in Driver.objects.all():
    print(f'{d.user.phone}: {d.status}')
"
```

---

## 🔐 All Test Accounts

| Type | Phone | Password |
|------|-------|----------|
| Rider | 9876543210 | securepassword123 |
| **Driver** | **1234567890** | **driver123** |
| Admin | admin | admin123 |

---

**Everything is configured! Just run `npx expo start` and scan the QR code!** 🎉
