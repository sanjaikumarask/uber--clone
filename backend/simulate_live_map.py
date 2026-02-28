
import os
import django
import time
import json
import random
import math
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.drivers.models import Driver
from apps.rides.models import Ride
from django.contrib.auth import get_user_model

User = get_user_model()

def simulate():
    channel_layer = get_channel_layer()
    print("🚀 Starting Live Map Simulation...")

    # 1. Setup Dummy Driver
    u, _ = User.objects.get_or_create(username="sim_driver", defaults={"email": "sim_driver@example.com", "phone": "9999999999", "first_name": "Simulated", "last_name": "Driver"})
    driver, _ = Driver.objects.get_or_create(id=999, defaults={"user": u, "status": "ONLINE"})
    
    driver.status = "ONLINE"
    driver.save()
    print(f"✅ Driver #{driver.id} is ONLINE")

    # 2. Setup Dummy Rider (simulated data, no DB record needed for visualization strictly, but good to have)
    rider_id = 888
    ride_id = 9999

    # Starting positions (Chennai)
    # Driver at Spencer Plaza
    d_lat, d_lng = 13.0581, 80.2641
    # Rider at Express Avenue
    r_lat, r_lng = 13.0587, 80.2615

    # Movement Logic (Circular)
    angle = 0

    try:
        while True:
            # Move Driver
            d_lat += 0.0001 * math.cos(angle)
            d_lng += 0.0001 * math.sin(angle)
            
            # Move Rider
            r_lat += 0.0001 * math.sin(angle)
            r_lng += 0.0001 * math.cos(angle)

            timestamp = int(time.time())

            # Broadcast Driver Update
            async_to_sync(channel_layer.group_send)(
                "admin_live_map",
                {
                    "type": "driver_location_updated",
                    "data": {
                        "driver_id": driver.id,
                        "lat": d_lat,
                        "lng": d_lng,
                        "status": "ONLINE",
                        "ts": timestamp
                    }
                }
            )

            # Broadcast Rider Update
            async_to_sync(channel_layer.group_send)(
                "admin_live_map",
                {
                    "type": "rider_location_updated",
                    "data": {
                        "ride_id": ride_id,
                        "rider_id": rider_id,
                        "lat": r_lat,
                        "lng": r_lng,
                        "ts": timestamp
                    }
                }
            )

            angle += 0.1
            time.sleep(1)  # Update every second
            print(f"📡 Sent updates: Driver({d_lat:.4f}, {d_lng:.4f}) | Rider({r_lat:.4f}, {r_lng:.4f})", end="\r")

    except KeyboardInterrupt:
        print("\n🛑 Simulation Stopped.")

if __name__ == "__main__":
    simulate()
