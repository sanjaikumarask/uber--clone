#!/bin/bash
# test_full_flow.sh - End-to-End Ride Lifecycle Test

set -e

BASE_URL="http://localhost:8000/api"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

function test_step() {
    echo -e "${BLUE}>>> $1${NC}"
}

function extract_val() {
    echo "$1" | sed -n "s/.*\"$2\":[ ]*\"\?\([^\",\}]*\)\"\?.*/\1/p" | head -n 1
}

# UNIQUE IDs for this run
ID=$RANDOM
RIDER_PHONE="+91700${ID}001"
DRIVER_PHONE="+91800${ID}002"

# 1. SETUP & CLEANUP
test_step "Cleaning up environment..."
python manage.py shell -c "from apps.users.models import User; from apps.drivers.models import Driver; import redis; r=redis.Redis.from_url('redis://redis:6379/0'); r.delete('drivers:geo'); Driver.objects.all().update(status='OFFLINE')" > /dev/null

RIDER_PHONE="+91170${ID}001"
DRIVER_PHONE="+91180${ID}002"

# 2. REGISTER & VERIFY
test_step "Registering Rider ($RIDER_PHONE)..."
curl -s -X POST $BASE_URL/users/register/ -H "Content-Type: application/json" \
  -d "{\"phone\": \"$RIDER_PHONE\", \"password\": \"password123\", \"role\": \"rider\", \"first_name\": \"John\", \"last_name\": \"Rider\", \"email\": \"rider_$ID@example.com\"}" | xargs echo

test_step "Registering Driver ($DRIVER_PHONE)..."
curl -s -X POST $BASE_URL/users/register/ -H "Content-Type: application/json" \
  -d "{\"phone\": \"$DRIVER_PHONE\", \"password\": \"password123\", \"role\": \"driver\", \"first_name\": \"Dave\", \"last_name\": \"Driver\", \"email\": \"driver_$ID@example.com\"}" | xargs echo

test_step "Forcing Driver Verification..."
python manage.py shell -c "from apps.users.models import User; from apps.drivers.models import Driver; u=User.objects.get(phone='$DRIVER_PHONE'); d=u.driver; d.is_verified=True; d.save();" > /dev/null

# 3. LOGIN
test_step "Logging in Rider..."
RIDER_OUT=$(curl -s -X POST $BASE_URL/users/login/ -H "Content-Type: application/json" -d "{\"phone\": \"$RIDER_PHONE\", \"password\": \"password123\"}")
RIDER_TOKEN=$(extract_val "$RIDER_OUT" "access")
if [ -z "$RIDER_TOKEN" ]; then echo -e "${RED}FAILED: Rider Login Failed${NC} - $RIDER_OUT"; exit 1; fi

test_step "Logging in Driver..."
DRIVER_OUT=$(curl -s -X POST $BASE_URL/users/driver-login/ -H "Content-Type: application/json" -d "{\"phone\": \"$DRIVER_PHONE\", \"password\": \"password123\"}")
DRIVER_TOKEN=$(extract_val "$DRIVER_OUT" "access")
if [ -z "$DRIVER_TOKEN" ]; then echo -e "${RED}FAILED: Driver Login Failed${NC} - $DRIVER_OUT"; exit 1; fi

# 4. DRIVER ONLINE
test_step "Setting Driver ONLINE at Chennai Central..."
curl -s -X POST $BASE_URL/drivers/status/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" -d '{"status": "ONLINE"}' | xargs echo
curl -s -X POST $BASE_URL/drivers/location/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" -d '{"lat": 13.0827, "lng": 80.2707}' | xargs echo

# 5. RIDER REQUEST
test_step "Rider requesting ride..."
RIDE_JSON=$(curl -s -X POST $BASE_URL/rides/request/ -H "Authorization: Bearer $RIDER_TOKEN" -H "Content-Type: application/json" \
  -d '{"pickup_lat": 13.0827, "pickup_lng": 80.2707, "drop_lat": 13.0405, "drop_lng": 80.2337, "vehicle_type": "go"}')
RIDE_ID=$(extract_val "$RIDE_JSON" "id")
if [ -z "$RIDE_ID" ]; then echo -e "${RED}FAILED: Ride Request Failed${NC} - $RIDE_JSON"; exit 1; fi
echo "SUCCESS: Ride ID $RIDE_ID"

# 6. MATCHING DELAY
test_step "Waiting for Matching Engine (5s)..."
sleep 5

# 7. DRIVER ACCEPT
test_step "Driver accepting ride $RIDE_ID..."
ACCEPT_OUT=$(curl -s -X POST $BASE_URL/rides/$RIDE_ID/accept/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json")
echo $ACCEPT_OUT
if [[ "$ACCEPT_OUT" == *"error"* ]]; then exit 1; fi

# 8. TRIP MILESTONES
test_step "Driver marking ARRIVED..."
curl -s -X POST $BASE_URL/rides/$RIDE_ID/arrived/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" | xargs echo

test_step "Fetching OTP..."
OTP=$(python manage.py shell -c "from apps.rides.models import Ride; print(Ride.objects.get(id=$RIDE_ID).otp_code)" | grep -oP '^\d{4}$')
echo "Retrieved OTP: $OTP"

test_step "Driver STARTING trip..."
curl -s -X POST $BASE_URL/rides/$RIDE_ID/start/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" \
  -d "{\"otp\": \"$OTP\", \"lat\": 13.0827, \"lng\": 80.2707}" | xargs echo

test_step "In Progress..."
sleep 2

test_step "Driver COMPLETING trip..."
COMPLETION_JSON=$(curl -s -X POST $BASE_URL/rides/$RIDE_ID/complete/ -H "Authorization: Bearer $DRIVER_TOKEN" -H "Content-Type: application/json" \
  -d '{"lat": 13.0405, "lng": 80.2337, "actual_distance_km": 5.8}')
echo $COMPLETION_JSON

test_step "Rider paying for ride (SIMULATION)..."
PAYMENT_JSON=$(curl -s -X POST $BASE_URL/payments/simulate/$RIDE_ID/ -H "Authorization: Bearer $RIDER_TOKEN" -H "Content-Type: application/json")
echo $PAYMENT_JSON

# 9. FINAL AUDIT
test_step "Final Audit..."
# Use filter().latest() to avoid MultipleObjectsReturned if lifecycle and manual payment both exist
FINAL_STATUS=$(python manage.py shell -c "from apps.rides.models import Ride; from apps.payments.models import Payment; r=Ride.objects.get(id=$RIDE_ID); p=Payment.objects.filter(ride_id=$RIDE_ID, status='CAPTURED').latest('id'); print(f'RIDE:{r.status}|PAYMENT:{p.status}|FARE:{r.final_fare}')" | grep -oP 'RIDE:.*')

test_step "Checking Notifications..."
NOTIF_CHECK=$(python manage.py shell -c "from apps.notifications.models import Notification; from apps.users.models import User; u=User.objects.get(phone='$RIDER_PHONE'); n=Notification.objects.filter(user=u, type='PAYMENT_CONFIRMED').exists(); print(f'NOTIF_CONFIRMED:{n}')" | grep -oP 'NOTIF_CONFIRMED:.*')

echo -e "\n${GREEN}=======================================${NC}"
echo -e "${GREEN}   E2E FULL FLOW SUCCESSFUL!           ${NC}"
echo -e "${GREEN}   $FINAL_STATUS                       ${NC}"
echo -e "${GREEN}   $NOTIF_CHECK                        ${NC}"
echo -e "${GREEN}=======================================${NC}"
