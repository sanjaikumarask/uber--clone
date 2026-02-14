# 🐛 Debugging Driver App Login

## Check These Things

### 1. Check Expo Console
When you run `npx expo start`, look at the terminal output for any errors or console.log messages.

### 2. Check Phone's Expo Go Logs
In Expo Go app:
- Shake your phone
- Tap "Debug Remote JS"
- Or look at the console in Expo Go

### 3. Test Backend Connectivity

#### From Your Phone's Browser
Visit: `http://192.169.1.137:8000/api/users/driver-login/`

**Expected:** Should show "Method not allowed" or similar Django error page  
**If you see this:** Backend is reachable ✅  
**If timeout/error:** Network issue ❌

### 4. Test Login from Terminal
```bash
curl -X POST http://192.169.1.137:8000/api/users/driver-login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"1234567890","password":"driver123"}'
```

**Expected:** JSON with `access`, `refresh`, and `user` fields

### 5. Common Issues

#### ❌ "Network request failed"
**Cause:** Phone can't reach your computer

**Solutions:**
1. Verify both on same WiFi
2. Check IP is correct: `hostname -I` (should be `192.169.1.137`)
3. Disable firewall temporarily:
   ```bash
   sudo ufw disable
   ```
4. Test from phone browser first

#### ❌ "Cannot reach server"
**Cause:** Backend not running or wrong IP

**Solutions:**
1. Check backend is running:
   ```bash
   docker ps | grep uber_backend
   ```
2. Restart backend:
   ```bash
   docker restart uber_backend
   ```
3. Verify IP in `src/services/api.ts` matches `hostname -I`

#### ❌ "Invalid credentials"
**Cause:** Wrong phone/password or account doesn't exist

**Solutions:**
1. Verify account exists:
   ```bash
   docker exec uber_backend python manage.py shell -c "
   from apps.users.models import User
   u = User.objects.get(phone='1234567890')
   print(f'Role: {u.role}, Has Driver: {hasattr(u, \"driver\")}')
   "
   ```
2. Reset password if needed:
   ```bash
   docker exec uber_backend python manage.py shell -c "
   from apps.users.models import User
   u = User.objects.get(phone='1234567890')
   u.set_password('driver123')
   u.save()
   print('Password reset')
   "
   ```

#### ❌ "Invalid server response"
**Cause:** Backend returning unexpected format

**Solutions:**
1. Check backend logs:
   ```bash
   docker logs --tail 50 uber_backend
   ```
2. Test endpoint manually (see step 4 above)

### 6. Enable Detailed Logging

The Login screen now has detailed console logging. Watch the Expo terminal for:
```
🔐 Attempting login...
📞 Phone: 1234567890
🌐 API URL: http://192.169.1.137:8000/api
✅ Login response received: {...}
💾 Saving auth data...
✅ Login successful!
```

Or errors:
```
❌ Login error: ...
❌ Error response: ...
❌ Error status: ...
```

### 7. Quick Test Script

Run this to verify everything:
```bash
#!/bin/bash
echo "=== Testing Driver App Setup ==="
echo ""

echo "1. Checking IP..."
IP=$(hostname -I | awk '{print $1}')
echo "   IP: $IP"
echo ""

echo "2. Checking backend..."
docker ps | grep uber_backend && echo "   ✅ Backend running" || echo "   ❌ Backend not running"
echo ""

echo "3. Testing driver login endpoint..."
curl -s -X POST http://localhost:8000/api/users/driver-login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"1234567890","password":"driver123"}' | jq -r '.user.phone' && echo "   ✅ Login works" || echo "   ❌ Login failed"
echo ""

echo "4. Checking driver account..."
docker exec uber_backend python manage.py shell -c "
from apps.users.models import User
try:
    u = User.objects.get(phone='1234567890')
    print(f'   ✅ Driver exists: {u.phone} ({u.role})')
except:
    print('   ❌ Driver not found')
"
echo ""

echo "5. Checking API config..."
grep -A 1 "YOUR_COMPUTER_IP" frontend/driver-app/src/services/api.ts | grep -o '"[0-9.]*"' && echo "   Check if this matches: $IP"
echo ""

echo "Done!"
```

Save as `test-driver-setup.sh`, make executable, and run:
```bash
chmod +x test-driver-setup.sh
./test-driver-setup.sh
```

---

## Still Not Working?

### Try Tunnel Mode
```bash
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npx expo start --tunnel
```

This creates a public URL that works even if local network has issues.

### Or Use Android Emulator
```bash
# Start Android Studio emulator first
npm run android
```

Emulator uses `10.0.2.2` to access localhost automatically.
