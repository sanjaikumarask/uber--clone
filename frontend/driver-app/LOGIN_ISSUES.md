# ⚠️ Common Login Issues

## ❌ "Invalid credentials" Error

### Issue 1: Wrong Phone Number
**Error:** `{"non_field_errors": ["Invalid credentials"]}`  
**Cause:** You entered `123456790` (9 digits) instead of `1234567890` (10 digits)

**Solution:** Use the correct phone number:
```
Phone: 1234567890  ← (10 digits, not 9!)
Password: driver123
```

---

### Issue 2: Token Expired (401 Error)
**Error:** `Failed to update location [AxiosError: Request failed with status code 401]`  
**Cause:** Your authentication token expired

**Solution:** 
1. The app will automatically log you out
2. Login again with correct credentials
3. Token will be refreshed

---

## ✅ Correct Login Credentials

### Driver Account
```
Phone: 1234567890
Password: driver123
```

### Rider Account
```
Phone: 9876543210
Password: securepassword123
```

### Admin Account
```
Username: admin
Password: admin123
```

---

## 🔍 Troubleshooting

### Check if Driver Exists
```bash
docker exec uber_backend python manage.py shell -c "
from apps.users.models import User
try:
    u = User.objects.get(phone='1234567890')
    print(f'✅ Driver exists: {u.phone}, Role: {u.role}')
except:
    print('❌ Driver not found')
"
```

### Reset Driver Password
```bash
docker exec uber_backend python manage.py shell -c "
from apps.users.models import User
u = User.objects.get(phone='1234567890')
u.set_password('driver123')
u.save()
print('✅ Password reset to: driver123')
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
print(f'✅ Created driver: {user.phone}')
"
```

---

## 📋 Quick Reference

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid credentials | Wrong phone/password | Use `1234567890` / `driver123` |
| 401 Unauthorized | Token expired | Login again |
| 400 Bad Request | Invalid data format | Check phone number format |
| Network Error | Can't reach backend | Check IP and network |

---

## 🎯 Remember

**Correct Phone Number:** `1234567890` (10 digits)  
**NOT:** `123456790` (9 digits) ❌

**Double-check your input before tapping Login!** ✅
