#!/bin/bash

echo "🔧 Fixing Nginx 502 Error..."
echo ""

# Check if backend is running
echo "1. Checking backend status..."
if docker ps | grep -q uber_backend; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend is not running!"
    echo "   Starting backend..."
    docker compose up -d backend
fi
echo ""

# Test backend directly
echo "2. Testing backend connection..."
if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
    echo "   ✅ Backend is accessible on port 8000"
else
    echo "   ❌ Backend not accessible!"
    echo "   Restarting backend..."
    docker restart uber_backend
    sleep 5
fi
echo ""

# Check Nginx
echo "3. Checking Nginx..."
if docker ps | grep -q uber_nginx; then
    echo "   ✅ Nginx is running"
    
    # Test Nginx config
    echo "   Testing Nginx configuration..."
    docker exec uber_nginx nginx -t 2>&1 | grep -q "successful" && echo "   ✅ Nginx config is valid" || echo "   ⚠️  Nginx config has issues"
else
    echo "   ❌ Nginx is not running!"
fi
echo ""

# Restart Nginx to pick up backend
echo "4. Restarting Nginx..."
docker restart uber_nginx
sleep 3
echo "   ✅ Nginx restarted"
echo ""

# Test the connection
echo "5. Testing Nginx → Backend connection..."
sleep 2
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/)
if [ "$RESPONSE" = "404" ] || [ "$RESPONSE" = "200" ]; then
    echo "   ✅ Nginx can reach backend (HTTP $RESPONSE)"
elif [ "$RESPONSE" = "502" ]; then
    echo "   ❌ Still getting 502 Bad Gateway"
    echo ""
    echo "   Possible issues:"
    echo "   1. Backend container name changed"
    echo "   2. Backend not listening on port 8000"
    echo "   3. Network issue between containers"
    echo ""
    echo "   Checking backend container name..."
    BACKEND_NAME=$(docker ps --format "{{.Names}}" | grep backend)
    echo "   Backend container: $BACKEND_NAME"
    echo ""
    echo "   Checking if backend is listening..."
    docker exec $BACKEND_NAME netstat -tuln 2>/dev/null | grep 8000 || echo "   ⚠️  Backend might not be listening on 8000"
else
    echo "   ⚠️  Unexpected response: HTTP $RESPONSE"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Backend direct:  http://localhost:8000/api/"
echo "Through Nginx:   http://localhost/api/"
echo ""
echo "Test with:"
echo "  curl http://localhost/api/"
echo ""
echo "View logs:"
echo "  docker compose logs -f nginx"
echo "  docker compose logs -f backend"
