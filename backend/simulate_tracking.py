import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import time
import math
import argparse
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.drivers.redis import update_driver_location
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone


def interpolate(p1, p2, t):
    return float(p1) + (float(p2) - float(p1)) * t


def get_bearing(lat1, lng1, lat2, lng2):
    """Calculate compass bearing between two lat/lng points."""
    d_lng = math.radians(lng2 - lng1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(d_lng) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(d_lng)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def group_send(channel_layer, group, payload):
    async_to_sync(channel_layer.group_send)(group, payload)


def broadcast_location(driver, ride, lat, lng, channel_layer, speed=40, prev_lat=None, prev_lng=None):
    """Send driver GPS ping to admin live map + rider tracking socket."""
    update_driver_location(driver.id, lat, lng)

    heading = None
    if prev_lat is not None and prev_lng is not None:
        heading = get_bearing(prev_lat, prev_lng, lat, lng)

    # ── Admin live map ────────────────────────────────────────────────
    admin_data = {
        "driver_id":  driver.id,
        "name":       driver.user.get_full_name() or driver.user.username,
        "phone":      driver.user.phone or "",
        "lat":        lat,
        "lng":        lng,
        "heading":    heading,
        "speed_kmh":  speed,
        "status":     driver.status,
        "ts":         int(time.time()),
        "ride": {
            "id":             ride.id,
            "status":         ride.status,
            "pickup":         {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
            "pickup_address": ride.pickup_address or "",
            "dropoff":        {"lat": float(ride.drop_lat),  "lng": float(ride.drop_lng)},
            "drop_address":   ride.drop_address or "",
            "polyline":       ride.planned_route_polyline,
            "distance_km":    round(float(ride.actual_distance_km), 2),
            "vehicle_type":   ride.vehicle_type,
            "rider_id":       ride.rider_id,
            "rider_name":     ride.rider.get_full_name() or ride.rider.username,
        }
    }
    group_send(channel_layer, "admin_live_map", {
        "type": "driver_location_updated",
        "data": admin_data,
    })

    # ── Rider tracking socket ─────────────────────────────────────────
    # RideConsumer.location_update / driver_location_updated handlers
    # both forward lat/lng/heading/eta under these flat keys:
    group_send(channel_layer, f"ride_{ride.id}", {
        "type":    "driver_location_updated",
        "lat":     lat,
        "lng":     lng,
        "heading": heading,
        "eta":     3,
        "ts":      int(time.time()),
    })


def broadcast_status(ride, channel_layer, extra=None):
    """Send ride_status_update to rider and admin_generic_event to admin."""
    payload = {
        "status":       ride.status,
        "vehicle_type": ride.vehicle_type,
        "otp_code":     ride.otp_code if ride.status == Ride.Status.ARRIVED else None,
    }
    if extra:
        payload.update(extra)

    # Rider socket
    group_send(channel_layer, f"ride_{ride.id}", {
        "type": "ride_status_update",
        "data": payload,
    })

    # Admin live map
    admin_data = {
        "ride_id":   ride.id,
        "status":    ride.status,
        "driver_id": ride.driver_id,
        "rider_id":  ride.rider_id,
        "ride":      None if ride.status in [Ride.Status.COMPLETED, Ride.Status.CANCELLED] else {
            "id":             ride.id,
            "status":         ride.status,
            "pickup":         {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
            "dropoff":        {"lat": float(ride.drop_lat),  "lng": float(ride.drop_lng)},
            "polyline":       ride.planned_route_polyline,
            "vehicle_type":   ride.vehicle_type,
            "rider_id":       ride.rider_id,
            "rider_name":     ride.rider.get_full_name() or ride.rider.username,
        },
    }
    if ride.driver:
        admin_data["driver_status"] = ride.driver.status
        admin_data["driver_name"] = ride.driver.user.get_full_name() or ride.driver.user.username

    group_send(channel_layer, "admin_live_map", {
        "type":  "admin_generic_event",
        "event": "RIDE_STATUS_UPDATED",
        "data":  admin_data,
    })


def follow_path(driver, ride, path, channel_layer, steps_per_segment=5, interval=0.25, speed_kmh=40, label="Moving"):
    """
    Sub-interpolates between path points for ultra-smooth movement.
    """
    if not path:
        return None, None

    prev_lat, prev_lng = path[0]
    total_points = len(path)
    
    for i in range(total_points - 1):
        p1 = path[i]
        p2 = path[i+1]
        
        for s in range(steps_per_segment):
            t = s / steps_per_segment
            lat = interpolate(p1[0], p2[0], t)
            lng = interpolate(p1[1], p2[1], t)
            
            broadcast_location(driver, ride, lat, lng, channel_layer, speed=speed_kmh,
                               prev_lat=prev_lat, prev_lng=prev_lng)
            prev_lat, prev_lng = lat, lng
            
            # Progress display
            progress = (i + (s/steps_per_segment)) / (total_points - 1)
            pct = int(progress * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r   {label}: [{bar}] {pct:3d}%  ({lat:.4f}, {lng:.4f})  ", end="", flush=True)
            
            time.sleep(interval)
            
    # Snap to final point
    last_lat, last_lng = path[-1]
    broadcast_location(driver, ride, last_lat, last_lng, channel_layer, speed=speed_kmh, prev_lat=prev_lat, prev_lng=prev_lng)
    print(f"\r   {label}: [████████████████████] 100%  ({last_lat:.4f}, {last_lng:.4f})  ")
    return last_lat, last_lng


def simulate_trip(ride_id):
    channel_layer = get_channel_layer()
    ride = Ride.objects.select_related("driver", "driver__user", "rider").get(id=ride_id)
    driver = ride.driver

    if not driver:
        print("Error: Ride has no driver assigned.")
        return

    from apps.tracking.geo import decode_route
    
    # Pre-decode path
    main_path = []
    if ride.planned_route_polyline:
        main_path = decode_route(ride.planned_route_polyline)
    
    print(f"\n🚗  Smooth Simulation | Ride #{ride_id} | Driver: {driver.user.get_full_name()}")

    # 1. Start / Assign
    if ride.status not in [Ride.Status.ASSIGNED, Ride.Status.ARRIVED, Ride.Status.ONGOING]:
        ride.status = Ride.Status.ASSIGNED
        ride.save(update_fields=["status", "updated_at"])
        driver.status = Driver.Status.BUSY
        driver.save(update_fields=["status"])
        broadcast_status(ride, channel_layer)
        print("✅  Status: ASSIGNED")

    # 2. Phase 1: To Pickup (Linear interpolation but smooth)
    pickup_lat, pickup_lng = float(ride.pickup_lat), float(ride.pickup_lng)
    start_lat = pickup_lat + 0.005
    start_lng = pickup_lng + 0.005
    
    # Create a 2-point path for to-pickup
    to_pickup_path = [(start_lat, start_lng), (pickup_lat, pickup_lng)]
    
    print("\n📍  Phase 1: Moving to pickup (High frequency pings)")
    last_lat, last_lng = follow_path(driver, ride, to_pickup_path, channel_layer, steps_per_segment=40, interval=0.1, label="To Pickup")

    # 3. Arrived
    from apps.rides.services.otp import generate_and_attach_otp
    ride.status = Ride.Status.ARRIVED
    ride.arrived_at = timezone.now()
    otp = generate_and_attach_otp(ride)
    ride.save(update_fields=["status", "arrived_at", "otp_code", "otp_expires_at", "updated_at"])
    broadcast_status(ride, channel_layer)
    print(f"\n✅  ARRIVED | OTP: {otp} | Waiting 3s...")
    time.sleep(3)

    # 4. Ongoing
    ride.status = Ride.Status.ONGOING
    ride.otp_verified_at = timezone.now()
    ride.save(update_fields=["status", "otp_verified_at", "updated_at"])
    broadcast_status(ride, channel_layer)
    print(f"\n🚀  ONGOING | Journey started!")

    if not main_path:
        # Fallback to linear if no polyline
        main_path = [(pickup_lat, pickup_lng), (float(ride.drop_lat), float(ride.drop_lng))]

    print(f"📍  Phase 2: Following road polyline ({len(main_path)} vertices)")
    last_lat, last_lng = follow_path(driver, ride, main_path, channel_layer, steps_per_segment=3, interval=0.15, speed_kmh=65, label="Trip Progress")

    # 5. Completed
    print("\n⏱️   Finalizing...")
    time.sleep(2)
    
    try:
        from apps.rides.services.complete_ride import complete_ride
        ride = complete_ride(ride.id)
        fare = float(ride.final_fare) if ride.final_fare else 0
        print(f"\n✅  Trip COMPLETED | Fare: ₹{fare:.2f}")

        group_send(channel_layer, f"ride_{ride.id}", {
            "type":    "ride_completed",
            "ride_id": ride.id,
            "fare":    fare,
        })
        print("📡  Broadcast sent.")
    except Exception as e:
        # In case complete_ride needs fresh object
        ride.refresh_from_db()
        fare = float(ride.final_fare) if ride.final_fare else 0
        print(f"\n✅  Trip COMPLETED | Fare: ₹{fare:.2f}")
        group_send(channel_layer, f"ride_{ride.id}", {
            "type":    "ride_completed",
            "ride_id": ride.id,
            "fare":    fare,
        })

    print("\n🏁  Simulation complete.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a full ride trip end-to-end")
    parser.add_argument("ride_id", type=int, help="ID of the ride to simulate")
    args = parser.parse_args()
    simulate_trip(args.ride_id)
