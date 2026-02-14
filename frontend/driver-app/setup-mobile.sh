#!/bin/bash

# Quick setup script for mobile testing

echo "🚀 Uber Driver App - Mobile Testing Setup"
echo "=========================================="
echo ""

# Get local IP
echo "📍 Finding your local IP address..."
LOCAL_IP=$(hostname -I | awk '{print $1}')

if [ -z "$LOCAL_IP" ]; then
    echo "❌ Could not detect IP automatically"
    echo "Please run: ip addr show | grep 'inet '"
    exit 1
fi

echo "✅ Your local IP: $LOCAL_IP"
echo ""

# Update api.ts
echo "📝 Updating driver app configuration..."
API_FILE="src/services/api.ts"

if [ -f "$API_FILE" ]; then
    # Backup original
    cp "$API_FILE" "$API_FILE.backup"
    
    # Update IP in file
    sed -i "s/const YOUR_COMPUTER_IP = \".*\"/const YOUR_COMPUTER_IP = \"$LOCAL_IP\"/" "$API_FILE"
    
    echo "✅ Updated $API_FILE with IP: $LOCAL_IP"
else
    echo "❌ File not found: $API_FILE"
    echo "Make sure you're in the driver-app directory"
    exit 1
fi

echo ""
echo "📱 Next steps:"
echo "1. Install Expo Go on your phone"
echo "2. Make sure phone and computer are on same WiFi"
echo "3. Run: npx expo start"
echo "4. Scan QR code with Expo Go app"
echo ""
echo "🔐 Test Driver Login:"
echo "   Phone: 1234567890"
echo "   Password: driver123"
echo ""
echo "💡 If driver doesn't exist, create one:"
echo "   docker exec -it uber_backend python manage.py shell"
echo "   Then run the commands from MOBILE_TESTING_GUIDE.md"
echo ""
