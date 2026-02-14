# 🚀 Nginx Production Deployment Guide

## ✅ **What's Configured:**

Your Uber Clone now uses **Nginx** as a reverse proxy with:

1. ✅ **Single Entry Point** - All traffic through port 80
2. ✅ **Rider Web App** - Served at `/`
3. ✅ **Admin Dashboard** - Served at `/admin-dashboard`
4. ✅ **Backend API** - Proxied at `/api/`
5. ✅ **Django Admin** - Proxied at `/admin/`
6. ✅ **WebSockets** - Proxied at `/ws/`
7. ✅ **Static Files** - Served at `/static/`
8. ✅ **Media Files** - Served at `/media/`
9. ✅ **Gzip Compression** - For faster loading
10. ✅ **Security Headers** - XSS, clickjacking protection
11. ✅ **Health Check** - At `/health`

---

## 🏗️ **Architecture:**

```
Internet
   ↓
[Port 80] → Nginx (Reverse Proxy)
   ├─→ /                    → Rider Web App (React SPA)
   ├─→ /admin-dashboard     → Admin Dashboard (React SPA)
   ├─→ /api/*               → Django Backend (Daphne)
   ├─→ /admin/*             → Django Admin
   ├─→ /ws/*                → WebSocket (Channels)
   ├─→ /static/*            → Static Files
   └─→ /media/*             → Media Files
```

---

## 📦 **Services:**

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| **Nginx** | uber_nginx | 80 | Reverse proxy & static files |
| **Backend** | uber_backend | 8000 (internal) | Django + Channels API |
| **Rider Web** | uber_rider_web | - | React build |
| **Admin Dashboard** | uber_admin_dashboard | - | React build |
| **PostgreSQL** | uber_postgres | 5432 (internal) | Database |
| **Redis** | uber_redis | 6379 (internal) | Cache & Channels |
| **Kafka** | uber_kafka | 9092 (internal) | Event streaming |
| **Celery** | uber_celery | - | Background tasks |

---

## 🚀 **Deployment Steps:**

### **1. Build and Start:**

```bash
# Stop existing containers
docker-compose down

# Build all services
docker-compose build

# Start everything
docker-compose up -d

# Check status
docker-compose ps
```

### **2. Collect Static Files:**

```bash
# Collect Django static files
docker exec uber_backend python manage.py collectstatic --noinput
```

### **3. Verify Nginx:**

```bash
# Check Nginx is running
docker logs uber_nginx

# Test Nginx configuration
docker exec uber_nginx nginx -t

# Reload Nginx (if config changed)
docker exec uber_nginx nginx -s reload
```

---

## 🌐 **Access URLs:**

### **Local Development:**
```
Rider Web:       http://localhost/
Admin Dashboard: http://localhost/admin-dashboard
Django Admin:    http://localhost/admin
API:             http://localhost/api/
WebSocket:       ws://localhost/ws/
Health Check:    http://localhost/health
```

### **Production (with domain):**
```
Rider Web:       https://yourdomain.com/
Admin Dashboard: https://yourdomain.com/admin-dashboard
Django Admin:    https://yourdomain.com/admin
API:             https://yourdomain.com/api/
```

---

## 🔧 **Configuration Files:**

### **1. Nginx Config** (`backend/nginx/nginx.conf`)
- Reverse proxy rules
- WebSocket support
- Gzip compression
- Security headers
- Caching rules

### **2. Docker Compose** (`docker-compose.yml`)
- Service definitions
- Volume mappings
- Network configuration
- Health checks

---

## 📊 **Nginx Features:**

### **Performance:**
- ✅ Gzip compression (6x smaller files)
- ✅ Static file caching (30 days)
- ✅ Keepalive connections
- ✅ Sendfile optimization

### **Security:**
- ✅ X-Frame-Options (clickjacking protection)
- ✅ X-Content-Type-Options (MIME sniffing protection)
- ✅ X-XSS-Protection
- ✅ Client body size limit (20MB)

### **Reliability:**
- ✅ Health check endpoint
- ✅ Automatic restart
- ✅ Connection timeouts
- ✅ WebSocket support (24h timeout)

---

## 🐛 **Troubleshooting:**

### **Nginx not starting:**
```bash
# Check logs
docker logs uber_nginx

# Test configuration
docker exec uber_nginx nginx -t

# Check if port 80 is available
sudo lsof -i :80
```

### **502 Bad Gateway:**
```bash
# Backend not running
docker ps | grep uber_backend

# Check backend logs
docker logs uber_backend

# Restart backend
docker restart uber_backend
```

### **Static files not loading:**
```bash
# Collect static files
docker exec uber_backend python manage.py collectstatic --noinput

# Check volume
docker exec uber_nginx ls -la /static/

# Reload Nginx
docker exec uber_nginx nginx -s reload
```

### **WebSocket connection fails:**
```bash
# Check Nginx WebSocket config
docker exec uber_nginx cat /etc/nginx/nginx.conf | grep -A 10 "location /ws/"

# Check backend WebSocket support
docker logs uber_backend | grep -i websocket
```

---

## 📱 **Mobile App Configuration:**

Update driver app to use Nginx:

```typescript
// frontend/driver-app/src/services/api.ts
const YOUR_SERVER_IP = "192.169.1.137";  // Your server IP

export const API_URL = `http://${YOUR_SERVER_IP}/api`;
export const WS_URL = `ws://${YOUR_SERVER_IP}/ws`;
```

---

## 🔒 **HTTPS Setup (Production):**

### **1. Get SSL Certificate:**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com
```

### **2. Update Nginx Config:**

Add to `nginx.conf`:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 📈 **Performance Monitoring:**

### **Check Nginx Stats:**
```bash
# Active connections
docker exec uber_nginx cat /var/log/nginx/access.log | wc -l

# Error rate
docker exec uber_nginx cat /var/log/nginx/error.log | tail -20

# Response times (if access log configured)
docker exec uber_nginx tail -100 /var/log/nginx/access.log
```

---

## 🎯 **Production Checklist:**

- [ ] Nginx running and healthy
- [ ] All services started
- [ ] Static files collected
- [ ] Health check responding
- [ ] Rider web accessible
- [ ] Admin dashboard accessible
- [ ] API endpoints working
- [ ] WebSocket connections working
- [ ] SSL certificate installed (production)
- [ ] Domain configured (production)
- [ ] Firewall rules set
- [ ] Backups configured

---

## 🚀 **Quick Commands:**

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Restart Nginx only
docker restart uber_nginx

# View Nginx logs
docker logs -f uber_nginx

# Reload Nginx config
docker exec uber_nginx nginx -s reload

# Test Nginx config
docker exec uber_nginx nginx -t

# Check all services
docker-compose ps

# Rebuild and restart
docker-compose up -d --build
```

---

## ✅ **Success Indicators:**

1. ✅ `docker-compose ps` shows all services as "Up"
2. ✅ `curl http://localhost/health` returns "healthy"
3. ✅ `http://localhost/` loads rider web app
4. ✅ `http://localhost/admin-dashboard` loads admin
5. ✅ `http://localhost/api/` returns Django API response
6. ✅ WebSocket connection works in browser console

---

## 🎊 **You're Production Ready!**

Your Uber Clone now has:
- ✅ Professional Nginx reverse proxy
- ✅ Optimized static file serving
- ✅ Gzip compression
- ✅ Security headers
- ✅ WebSocket support
- ✅ Health monitoring
- ✅ Easy HTTPS upgrade path

**Deploy with confidence!** 🚀
