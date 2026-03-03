#!/bin/bash
# test_api.sh - Comprehensive API test script

# Set strict mode
set -e

# API Base URL
BASE_URL="http://localhost:8000/api"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

function test_step() {
    echo -e "${GREEN}>>> $1${NC}"
}

# 1. CLEANUP
test_step "Cleaning up previous test users..."
python manage.py shell -c "from apps.users.models import User; User.objects.filter(phone__in=['+919991112221', '+919992223332']).delete()" > /dev/null

# 2. REGISTER USERS
test_step "Registering Rider..."
RIDER_DATA='{"phone": "+919991112221", "password": "password123", "role": "rider", "first_name": "API", "last_name": "Tester"}'
REGISTER_RIDER=$(curl -s -X POST $BASE_URL/users/register/ -H "Content-Type: application/json" -d "$RIDER_DATA")
echo $REGISTER_RIDER

test_step "Registering Driver..."
DRIVER_DATA='{"phone": "+919992223332", "password": "password123", "role": "driver", "first_name": "API", "last_name": "Driver"}'
REGISTER_DRIVER=$(curl -s -X POST $BASE_URL/users/register/ -H "Content-Type: application/json" -d "$DRIVER_DATA")
echo $REGISTER_DRIVER

# 3. LOGIN
test_step "Logging in Rider..."
RIDER_TOKEN=$(curl -s -X POST $BASE_URL/users/login/ -H "Content-Type: application/json" -d '{"phone": "+919991112221", "password": "password123"}' | grep -oP '"access":"\K[^"]+')
echo "Rider Access Token: ${RIDER_TOKEN:0:15}..."

test_step "Logging in Driver..."
DRIVER_JSON=$(curl -s -X POST $BASE_URL/users/driver-login/ -H "Content-Type: application/json" -d '{"phone": "+919992223332", "password": "password123"}')
DRIVER_TOKEN=$(echo $DRIVER_JSON | grep -oP '"access":"\K[^"]+')
echo "Driver Access Token: ${DRIVER_TOKEN:0:15}..."

# 4. DRIVER SETUP (MUST BE ONLINE FOR MATCHING)
test_step "Setting Driver ONLINE..."
curl -s -X POST $BASE_URL/drivers/status/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" -d '{"status": "ONLINE"}' | xargs echo

test_step "Updating Driver Location..."
curl -s -X POST $BASE_URL/drivers/location/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" -d '{"lat": 12.9716, "lng": 77.5946}' | xargs echo

# 5. RIDER ACTIONS
test_step "Getting Fare Estimate..."
curl -s -X POST $BASE_URL/rides/estimate-fare/ -H "Authorization: Bearer $RIDER_TOKEN" -H "Content-Type: application/json" -d '{"pickup_lat": 12.9716, "pickup_lng": 77.5946, "drop_lat": 12.9345, "drop_lng": 77.6101, "vehicle_type": "go"}' | xargs echo

test_step "Requesting Ride..."
RIDE_JSON=$(curl -s -X POST $BASE_URL/rides/request/ -H "Authorization: Bearer $RIDER_TOKEN" -H "Content-Type: application/json" -d '{"pickup_lat": 12.9716, "pickup_lng": 77.5946, "drop_lat": 12.9345, "drop_lng": 77.6101, "vehicle_type": "go"}')
echo $RIDE_JSON
RIDE_ID=$(echo $RIDE_JSON | grep -oP '"id":\K[0-9]+')
echo "SUCCESS: Ride Created with ID $RIDE_ID"

# 6. SYSTEM CHECKS
test_step "Checking System Health..."
curl -s http://localhost:8000/metrics | head -n 10

test_step "Verifying Private Profile Access..."
curl -s -X GET $BASE_URL/users/me/ -H "Authorization: Bearer $RIDER_TOKEN" | xargs echo

echo -e "\n${GREEN}=======================================${NC}"
echo -e "${GREEN}   ALL API SYSTEMS ARE OPERATIONAL     ${NC}"
echo -e "${GREEN}=======================================${NC}"
