#!/bin/bash

echo "🔨 Building and deploying rider web app to Nginx..."
echo ""

# Build rider web
echo "1. Building rider web app..."
cd frontend/rider-web
npm run build
if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi
echo "✅ Build complete"
echo ""

# Copy to Nginx
echo "2. Copying build to Nginx..."
cd ../..
docker cp frontend/rider-web/dist/. uber_nginx:/usr/share/nginx/html/
if [ $? -ne 0 ]; then
    echo "❌ Copy failed!"
    exit 1
fi
echo "✅ Files copied"
echo ""

# Restart Nginx
echo "3. Restarting Nginx..."
docker restart uber_nginx
sleep 2
echo "✅ Nginx restarted"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Access at: http://localhost/"
echo ""
echo "Note: For development, use http://localhost:5173 instead"
