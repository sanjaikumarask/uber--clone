import math
import os
import time

import django
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

from apps.drivers.models import Driver

User = get_user_model()


def simulate_3_drivers():
    channel_layer = get_channel_layer()
    print("🚀 Starting 3-Driver Live Map Simulation...")

    # 1. Setup Drivers
    driver_data = [
        {"id": 7771, "username": "demo_driver_1", "name": "Driver Alpha"},
        {"id": 7772, "username": "demo_driver_2", "name": "Driver Beta"},
        {"id": 7773, "username": "demo_driver_3", "name": "Driver Gamma"},
    ]

    drivers = []
    for data in driver_data:
        # Try finding by username first
        u = User.objects.filter(username=data["username"]).first()
        if not u:
            # If not found, try finding by phone to avoid IntegrityError
            phone = f"7700000{data['id']}"
            u = User.objects.filter(phone=phone).first()

        if not u:
            # Still not found, create it
            u = User.objects.create(
                username=data["username"],
                email=f"{data['username']}@example.com",
                phone=f"7700000{data['id']}",
                first_name=data["name"].split()[0],
                last_name=data["name"].split()[1],
            )

        d, _ = Driver.objects.get_or_create(
            user=u, defaults={"id": data["id"], "status": "ONLINE"}
        )
        d.status = "ONLINE"
        d.save()
        drivers.append(d)
        print(f"✅ {data['name']} (ID: {d.id}) is ONLINE")

    # Starting positions (Chennai - around map center 13.0827, 80.2707)
    positions = [
        {"lat": 13.0840, "lng": 80.2720, "angle": 0},
        {"lat": 13.0810, "lng": 80.2680, "angle": 2},
        {"lat": 13.0850, "lng": 80.2650, "angle": 4},
    ]

    try:
        while True:
            timestamp = int(time.time())

            for i, d in enumerate(drivers):
                pos = positions[i]
                # Move pattern: Each driver moves in a slightly different circle/phase
                phase = pos["angle"] + (i * 1.5)

                # Larger movement (0.00015 degrees) so it's clearly visible
                pos["lat"] += 0.00015 * math.cos(phase)
                pos["lng"] += 0.00015 * math.sin(phase)
                pos["angle"] += 0.1

                # 1. Update Database (for API visibility)
                d.last_lat = pos["lat"]
                d.last_lng = pos["lng"]
                d.save(update_fields=["last_lat", "last_lng"])

                # 2. Update Redis Geo Index (CRITICAL: for Nearby Drivers API)
                from apps.drivers.redis import update_driver_location

                update_driver_location(d.id, pos["lat"], pos["lng"])

                # 3. Broadcast to Admin Live Map (for real-time animation)
                async_to_sync(channel_layer.group_send)(
                    "admin_live_map",
                    {
                        "type": "driver_location_updated",
                        "data": {
                            "driver_id": d.id,
                            "name": d.user.get_full_name() or d.user.username,
                            "lat": pos["lat"],
                            "lng": pos["lng"],
                            "status": "ONLINE",
                            "ts": timestamp,
                        },
                    },
                )

            time.sleep(1)  # Faster updates for smoother map motion
            print(
                f"📡 Updates @ {timestamp}: D1({positions[0]['lat']:.4f}), D2({positions[1]['lat']:.4f}), D3({positions[2]['lat']:.4f})",
                end="\r",
            )

    except KeyboardInterrupt:
        print("\n🛑 Simulation Stopped.")


if __name__ == "__main__":
    simulate_3_drivers()
