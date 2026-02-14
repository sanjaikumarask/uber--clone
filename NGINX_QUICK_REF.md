# 🚀 Nginx Quick Reference

## 📦 **One-Command Deploy:**
```bash
./deploy.sh
```

## 🌐 **URLs:**
```
Rider:  http://localhost/
Admin:  http://localhost/admin-dashboard
API:    http://localhost/api/
Health: http://localhost/health
```

## 🔧 **Common Commands:**
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart Nginx
docker restart uber_nginx

# View logs
docker logs -f uber_nginx

# Test config
docker exec uber_nginx nginx -t

# Reload config
docker exec uber_nginx nginx -s reload

# Collect static
docker exec uber_backend python manage.py collectstatic --noinput
```

## 🐛 **Quick Fixes:**
```bash
# 502 Error
docker restart uber_backend

# Static files not loading
docker exec uber_backend python manage.py collectstatic --noinput
docker restart uber_nginx

# Check all services
docker-compose ps

# View all logs
docker-compose logs -f
```

## ✅ **Health Check:**
```bash
curl http://localhost/health
# Should return: "healthy"
```

## 📊 **Service Status:**
```bash
docker-compose ps
```

## 🎯 **Files:**
- Config: `backend/nginx/nginx.conf`
- Docker: `docker-compose.yml`
- Deploy: `./deploy.sh`
- Docs: `NGINX_DEPLOYMENT.md`
