# 🔧 Fixing Nginx 502 Bad Gateway Error

## 🐛 **Problem:**

Nginx logs show:
```
connect() failed (111: Connection refused) while connecting to upstream
upstream: "http://172.18.0.10:8000/api/"
```

This means Nginx can't connect to the Django backend.

---

## ✅ **Quick Fix:**

### **Run the fix script:**
```bash
./fix-nginx.sh
```

This will:
1. Check if backend is running
2. Test backend connectivity
3. Restart Nginx
4. Verify the connection

---

## 🔍 **Manual Diagnosis:**

### **1. Check if backend is running:**
```bash
docker ps | grep uber_backend
```

**Expected:** Should show `uber_backend` container running

### **2. Test backend directly:**
```bash
curl http://localhost:8000/api/
```

**Expected:** Should return HTML or JSON response (not connection refused)

### **3. Check Nginx can see backend:**
```bash
docker exec uber_nginx ping -c 2 backend
```

**Expected:** Should get ping responses

### **4. Check backend logs:**
```bash
docker compose logs backend | tail -20
```

**Look for:** Any errors or if it's receiving requests

---

## 🛠️ **Solutions:**

### **Solution 1: Restart Backend**
```bash
docker restart uber_backend
sleep 5
docker restart uber_nginx
```

### **Solution 2: Restart All Services**
```bash
docker compose restart
```

### **Solution 3: Full Rebuild**
```bash
docker compose down
docker compose up -d
```

### **Solution 4: Check Network**
```bash
# Check if containers are on same network
docker network inspect uber-backend_default

# Should show both nginx and backend containers
```

---

## 🎯 **Root Causes & Fixes:**

### **Cause 1: Backend Not Running**
**Symptom:** `docker ps` doesn't show `uber_backend`

**Fix:**
```bash
docker compose up -d backend
```

### **Cause 2: Backend Crashed**
**Symptom:** Backend logs show errors

**Fix:**
```bash
docker compose logs backend
# Fix the error shown
docker restart uber_backend
```

### **Cause 3: Wrong Container Name**
**Symptom:** Nginx looking for wrong container

**Fix:** Update `backend/nginx/nginx.conf`:
```nginx
upstream backend_api {
    server backend:8000;  # Make sure this matches container name
}
```

### **Cause 4: Backend Not Listening**
**Symptom:** Backend running but not accepting connections

**Fix:**
```bash
# Check if backend is listening on 8000
docker exec uber_backend netstat -tuln | grep 8000

# Should show: tcp   0.0.0.0:8000
```

### **Cause 5: Network Issue**
**Symptom:** Containers can't communicate

**Fix:**
```bash
docker compose down
docker compose up -d
```

---

## ✅ **Verification:**

### **Test 1: Backend Direct**
```bash
curl http://localhost:8000/api/
```
**Expected:** HTML/JSON response

### **Test 2: Through Nginx**
```bash
curl http://localhost/api/
```
**Expected:** Same response as Test 1

### **Test 3: Health Check**
```bash
curl http://localhost/health
```
**Expected:** "healthy"

---

## 📊 **Current Status Check:**

```bash
# All services status
docker compose ps

# Backend status
docker ps | grep uber_backend

# Nginx status  
docker ps | grep uber_nginx

# Test connectivity
curl -I http://localhost:8000/api/  # Direct
curl -I http://localhost/api/       # Through Nginx
```

---

## 🚀 **Quick Commands:**

```bash
# Restart everything
docker compose restart

# Restart just backend
docker restart uber_backend

# Restart just nginx
docker restart uber_nginx

# View logs
docker compose logs -f nginx
docker compose logs -f backend

# Test connection
curl http://localhost/api/
```

---

## 💡 **Why This Happens:**

1. **Backend crashes** → Nginx can't connect
2. **Backend starts slowly** → Nginx tries before backend is ready
3. **Network changes** → Container IPs change
4. **Config mismatch** → Nginx looking for wrong service name

---

## ✅ **After Fix:**

You should see:
```bash
$ curl http://localhost/api/
# Returns Django API response (not 502)

$ curl http://localhost/health
healthy
```

---

## 🎯 **Prevention:**

Add health checks to `docker-compose.yml`:

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s

nginx:
  depends_on:
    backend:
      condition: service_healthy
```

This ensures Nginx only starts after backend is ready.

---

**Run `./fix-nginx.sh` to automatically diagnose and fix!** 🚀
