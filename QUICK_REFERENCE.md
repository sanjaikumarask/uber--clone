# 🚗 Uber Clone - Quick Reference

## Test Accounts

### Rider Account
- **Phone:** `9876543210`
- **Password:** `securepassword123`
- **Login URL:** `http://localhost:5173` (Rider Web App)
- **Endpoint:** `POST /api/users/login/`

### Driver Account  
- **Phone:** `1234567890`
- **Password:** `driver123`
- **Login via:** Expo Go App (Driver Mobile App)
- **Endpoint:** `POST /api/users/driver-login/`

### Admin Account
- **Username:** `admin`
- **Password:** `admin123`
- **Login URL:** `http://localhost:5174` (Admin Dashboard)
- **Endpoint:** `POST /api/users/admin-login/`

---

## Available Drivers

Run this to see all drivers:
```bash
docker exec uber_backend python manage.py shell -c "
from apps.drivers.models import Driver
for d in Driver.objects.all():
    print(f'Phone: {d.user.phone}, Status: {d.status}, ID: {d.id}')
"
```

Current drivers:
- `9999999999` - Status: BUSY
- `1234567890` - Status: OFFLINE ✅ **Use this one**

---

## Quick Start Commands

### Start Backend
```bash
cd /home/sanjai/dev/uber-backend
docker-compose up -d
```

### Start Rider Web App
```bash
cd /home/sanjai/dev/uber-backend/frontend/rider-web
npm run dev
# Opens on http://localhost:5173
```

### Start Admin Dashboard
```bash
cd /home/sanjai/dev/uber-backend/admin-dashboard
npm run dev
# Opens on http://localhost:5174
```

### Start Driver Mobile App
```bash
cd /home/sanjai/dev/uber-backend/frontend/driver-app
npx expo start
# Scan QR code with Expo Go
```

---

## API Endpoints

### Authentication
- `POST /api/users/register/` - Register rider
- `POST /api/users/login/` - Rider login
- `POST /api/users/driver-login/` - Driver login
- `POST /api/users/admin-login/` - Admin login
- `GET /api/users/me/` - Get current user

### Rides (Rider)
- `GET /api/rides/active/` - Get active ride
- `POST /api/rides/request/` - Request new ride
- `GET /api/rides/{id}/` - Get ride details
- `POST /api/rides/{id}/cancel/` - Cancel ride

### Rides (Driver)
- `POST /api/rides/{id}/accept/` - Accept ride offer
- `POST /api/rides/{id}/reject/` - Reject ride offer
- `POST /api/rides/{id}/arrived/` - Mark arrived at pickup
- `POST /api/rides/{id}/start/` - Start ride (with OTP)
- `POST /api/rides/{id}/complete/` - Complete ride
- `POST /api/rides/{id}/no-show/` - Mark no-show

### Driver
- `GET /api/drivers/me/` - Get driver profile
- `POST /api/drivers/status/` - Update status (ONLINE/OFFLINE)
- `POST /api/drivers/location/` - Update location

### Tracking
- `POST /api/tracking/update-location/` - Update driver location

---

## Testing Flow

### 1. Setup Driver
```bash
# Login to driver app with:
Phone: 1234567890
Password: driver123

# Go ONLINE
```

### 2. Request Ride (Rider)
```bash
# Login to rider web with:
Phone: 9876543210
Password: securepassword123

# Or register new account
# Book a ride
```

### 3. Accept Ride (Driver)
```bash
# Driver receives offer
# Accept ride
# Navigate to pickup
# Mark as arrived
```

### 4. Start Ride
```bash
# Rider sees OTP in their app
# Driver enters OTP
# Ride starts
```

### 5. Complete Ride
```bash
# Driver navigates to destination
# Marks ride as complete
# Both apps update
```

---

## Troubleshooting

### Check Backend Logs
```bash
docker logs -f uber_backend
```

### Check Database
```bash
docker exec -it uber_backend python manage.py shell
```

### Reset Driver Status
```bash
docker exec uber_backend python manage.py shell -c "
from apps.drivers.models import Driver
d = Driver.objects.get(user__phone='1234567890')
d.status = 'OFFLINE'
d.save()
print(f'Driver status: {d.status}')
"
```

### Create New Driver
```bash
docker exec uber_backend python manage.py shell -c "
from apps.users.models import User
from apps.drivers.models import Driver

user = User.objects.create_user(
    username='5555555555',
    phone='5555555555',
    password='driver123',
    role='driver',
    first_name='New',
    last_name='Driver'
)

Driver.objects.create(user=user, status='OFFLINE')
print(f'Created driver: {user.phone}')
"
```

---

## Common Issues

### ❌ Login Failed
- **Check:** Are you using the correct phone number?
  - Rider: `9876543210`
  - Driver: `1234567890`
- **Check:** Are you using the correct endpoint?
  - Rider: `/api/users/login/`
  - Driver: `/api/users/driver-login/`

### ❌ Network Request Failed (Mobile)
- Update IP in `driver-app/src/services/api.ts`
- Ensure phone and computer on same WiFi
- Check firewall settings

### ❌ Ride Not Appearing
- Check driver is ONLINE
- Check backend logs for matching errors
- Verify ride status in database

---

## Port Reference

- **8000** - Backend API
- **5173** - Rider Web App
- **5174** - Admin Dashboard
- **5432** - PostgreSQL
- **6379** - Redis
- **9092** - Kafka
- **19000-19001** - Expo Dev Server

---

## Need Help?

1. Check backend logs: `docker logs -f uber_backend`
2. Check database state using Django shell
3. Verify all services running: `docker-compose ps`
4. Restart backend: `docker restart uber_backend`

**Remember:** Use phone `1234567890` for driver login, NOT `9876543210`!
