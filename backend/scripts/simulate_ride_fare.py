import os
import sys
from datetime import timedelta
from decimal import Decimal

import django
from django.utils import timezone

# Setup Django Environment
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.cache import cache

from apps.drivers.models import Driver
from apps.rides.fare_models import FareConfig
from apps.rides.models import Ride
from apps.rides.services.complete_ride import complete_ride
from apps.rides.services.lifecycle import update_ride_status
from apps.rides.services.waiting_detector import _cache_key
from apps.users.models import User

SEPARATOR = "=================================="

print("\n🚗 \033[1;36mUBER FARE SIMULATOR\033[0m 🚗")
print(f"{SEPARATOR}\n")

# 1. Ensure a config exists
config, _ = FareConfig.objects.get_or_create(
    vehicle_type="go",
    defaults={
        "base_fare": Decimal("60.00"),
        "base_distance_km": Decimal("2.00"),
        "per_km_rate": Decimal("20.00"),
        "waiting_free_minutes": 2,
        "waiting_per_minute": Decimal("2.00"),
        "minimum_fare": Decimal("50.00"),
        "surge_multiplier": Decimal("1.00"),
        "platform_commission_pct": Decimal("20.00"),
    },
)
print(f"✅ Loading \033[1;33m{config.get_vehicle_type_display()}\033[0m Configuration:")
print(
    f"   ► Base Fare: ₹{config.base_fare} (includes first {config.base_distance_km}km)"
)
print(f"   ► Per KM Rate: ₹{config.per_km_rate}/km")
print(
    f"   ► Waiting Fee: ₹{config.waiting_per_minute}/min (after {config.waiting_free_minutes}m free)\n"
)

# 2. Setup mock users
rider_user, _ = User.objects.get_or_create(
    phone="+10000000001",
    defaults={
        "username": "test_rider_1",
        "first_name": "Test",
        "last_name": "Rider",
        "role": "RIDER",
    },
)
driver_user, _ = User.objects.get_or_create(
    phone="+10000000002",
    defaults={
        "username": "test_driver_1",
        "first_name": "Test",
        "last_name": "Driver",
        "role": "DRIVER",
    },
)
driver, _ = Driver.objects.get_or_create(
    user=driver_user, defaults={"status": "ONLINE", "is_verified": True}
)

# 3. Create a Ride
ride = Ride.objects.create(
    rider=rider_user,
    driver=driver,
    vehicle_type="go",
    status=Ride.Status.ASSIGNED,
    pickup_lat="12.9716",
    pickup_lng="77.5946",
    drop_lat="12.9352",
    drop_lng="77.6245",
    planned_distance_km=Decimal("5.0"),
    base_fare=Decimal("120.00"),  # Originally quoted fare
)
print("📍 Need a ride from Bangalore Central to Koramangala (5km)")
print(f"{SEPARATOR}\n")

# 4. Driver Arrives (Start Waiting Time)
update_ride_status(ride, Ride.Status.ARRIVED)
ride.arrived_at = timezone.now() - timedelta(
    minutes=7
)  # Pretend driver arrived 7 mins ago
ride.save(update_fields=["arrived_at"])
print("🚘 Driver Arrived 7 minutes ago.")

# 5. Simulate Redis GPS Waiting (Driver waits outside)
# Instead of pinging GPS coords, we directly inject the waiting state into Redis
simulated_waiting_seconds = 7 * 60
cache.set(
    _cache_key(ride.id),
    {
        "is_waiting": False,
        "waiting_since": None,
        "accumulated_secs": simulated_waiting_seconds,
        "low_speed_since": None,
    },
    3600,
)

print(
    f"⏱️ Redis tracked vehicle wait: {simulated_waiting_seconds/60} mins outside (420 seconds)"
)

# 6. Trip Starts
update_ride_status(ride, Ride.Status.ONGOING)
ride.otp_verified_at = timezone.now() - timedelta(minutes=20)  # 20 minute trip
ride.save(update_fields=["otp_verified_at"])
print("🟢 Rider boards. Trip Starts!\n")

# 7. Trip Completes (Driver took a longer route)
ride.actual_distance_km = Decimal("8.5")  # Drove 8.5km instead of 5km
ride.save(update_fields=["actual_distance_km"])
print("🏁 Driver completes trip. Actual Distance: 8.5km\n")

# 8. Run Complete Ride Pipeline (Final Fare Gen)
completed_ride = complete_ride(ride_id=ride.id)
completed_ride.refresh_from_db()

# 9. Print Breakdown
print(SEPARATOR)
print(f"💰 \033[1;32mFINAL RECEIPT for Ride #{ride.id}\033[0m")
print(SEPARATOR)

breakdown = completed_ride.fare_breakdown
print("👉 Base Config:")
print(f"   Base + {config.base_distance_km}km = ₹{breakdown.get('base_fare')}")

print("\n👉 Distance Charge (8.5km total):")
print(f"   First {config.base_distance_km}km: Included")
print(
    f"   Extra {Decimal('8.5') - config.base_distance_km}km @ ₹{config.per_km_rate}/km: ₹{breakdown.get('distance_charge')}"
)

print("\n👉 Waiting Charge (7 minutes):")
print(f"   First {config.waiting_free_minutes} minutes: Free")
print(
    f"   Extra 5 minutes @ ₹{config.waiting_per_minute}/min: ₹{breakdown.get('waiting_charge')}"
)

print(
    f"\n👉 Subtotal: ₹{float(breakdown.get('base_fare', 0)) + float(breakdown.get('distance_charge', 0)) + float(breakdown.get('waiting_charge', 0))}"
)
print(f"👉 Surge: {breakdown.get('surge_multiplier')}x")

print(SEPARATOR)
print(f"💳 \033[1;36mRIDER PAYS: ₹{completed_ride.final_fare}\033[0m")
print(SEPARATOR)
