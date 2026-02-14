# 📱 Setup for Physical Android Device (USB Debugging)

## ✅ You're Using Physical Device - Perfect!

Since you're using a physical Android device with USB debugging, we need to use **ADB reverse port forwarding**. This makes your phone able to access your computer's `localhost:8000`.

---

## 🔧 Setup Steps

### 1. Enable USB Debugging (Already Done ✅)
You already have this working since you're running the app!

### 2. Set Up Port Forwarding
Run this command **once** (or after reconnecting your phone):

```bash
adb reverse tcp:8000 tcp:8000
```

**What this does:** Makes `localhost:8000` on your phone point to `localhost:8000` on your computer (where Docker is running).

### 3. Verify ADB Connection
```bash
adb devices
```

**Expected output:**
```
List of devices attached
XXXXXXXXXX      device
```

If you see "unauthorized", unlock your phone and accept the USB debugging prompt.

### 4. Restart Expo
```bash
# In your driver-app terminal, press 'r' to reload
# Or restart:
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npx expo start
```

### 5. Try Login Again
- Phone: `1234567890`
- Password: `driver123`

---

## 🧪 Test Port Forwarding

### Test from your computer:
```bash
curl http://localhost:8000/api/users/driver-login/
```

**Expected:** Django error page (proves backend is accessible)

### Test from ADB shell (simulates your phone):
```bash
adb shell curl http://localhost:8000/api/users/driver-login/
```

**Expected:** Same Django error page (proves port forwarding works)

---

## 🔄 If Port Forwarding Stops Working

Sometimes you need to re-run the reverse command:

```bash
# Remove old forwarding
adb reverse --remove tcp:8000

# Add it again
adb reverse tcp:8000 tcp:8000

# Verify it's set up
adb reverse --list
```

**Expected output:**
```
tcp:8000 tcp:8000
```

---

## 📋 Complete Setup Script

Save this as `setup-adb.sh`:

```bash
#!/bin/bash

echo "🔧 Setting up ADB port forwarding for Driver App"
echo ""

echo "1. Checking ADB connection..."
adb devices | grep -q "device$" && echo "   ✅ Device connected" || echo "   ❌ No device found"
echo ""

echo "2. Setting up port forwarding..."
adb reverse tcp:8000 tcp:8000 && echo "   ✅ Port 8000 forwarded" || echo "   ❌ Failed"
echo ""

echo "3. Verifying forwarding..."
adb reverse --list | grep "tcp:8000" && echo "   ✅ Forwarding active" || echo "   ❌ Not active"
echo ""

echo "4. Testing backend connectivity..."
adb shell curl -s http://localhost:8000/api/users/driver-login/ > /dev/null 2>&1 && echo "   ✅ Backend reachable from device" || echo "   ❌ Cannot reach backend"
echo ""

echo "✅ Setup complete!"
echo ""
echo "Now try logging in with:"
echo "   Phone: 1234567890"
echo "   Password: driver123"
```

Make it executable and run:
```bash
chmod +x setup-adb.sh
./setup-adb.sh
```

---

## 🐛 Troubleshooting

### ❌ "adb: command not found"
Install Android SDK platform tools:
```bash
sudo apt-get install android-tools-adb android-tools-fastboot
```

### ❌ "error: no devices/emulators found"
1. Check USB cable is connected
2. Check USB debugging is enabled on phone
3. Try different USB port
4. Run: `adb kill-server && adb start-server`

### ❌ "error: device unauthorized"
1. Unlock your phone
2. Accept the "Allow USB debugging?" prompt
3. Check "Always allow from this computer"

### ❌ Still getting "Network Error"
1. Verify backend is running:
   ```bash
   docker ps | grep uber_backend
   ```
2. Test backend locally:
   ```bash
   curl http://localhost:8000/api/users/driver-login/
   ```
3. Check port forwarding is active:
   ```bash
   adb reverse --list
   ```
4. Restart everything:
   ```bash
   adb reverse --remove-all
   adb reverse tcp:8000 tcp:8000
   # Then reload app (press 'r' in Expo)
   ```

---

## 🎯 Quick Reference

| Command | Purpose |
|---------|---------|
| `adb devices` | List connected devices |
| `adb reverse tcp:8000 tcp:8000` | Forward port 8000 |
| `adb reverse --list` | Show active forwards |
| `adb reverse --remove tcp:8000` | Remove forwarding |
| `adb reverse --remove-all` | Remove all forwards |
| `adb shell curl localhost:8000` | Test from phone |

---

## ✅ What's Changed

The app now uses `localhost:8000` instead of `10.0.2.2` or your IP address. This works because ADB reverse makes `localhost` on your phone point to your computer.

**Advantages:**
- ✅ Faster than WiFi
- ✅ More reliable
- ✅ Works even if WiFi is off
- ✅ No need to update IP addresses

**Just remember:** Run `adb reverse tcp:8000 tcp:8000` once after connecting your phone!

---

## 🚀 Ready to Test!

1. ✅ USB debugging enabled
2. ✅ Phone connected via USB
3. ✅ Run: `adb reverse tcp:8000 tcp:8000`
4. ✅ Reload app (press 'r' in Expo)
5. ✅ Login with `1234567890` / `driver123`

**It should work now!** 🎉
