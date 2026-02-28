# apps/tracking/consumers/driver_location.py

import json
import time
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

from apps.rides.models import Ride
from apps.tracking.geo import (
    decode_route,
    snap_to_route,
    is_deviated,
    accumulate_distance,
)
from apps.tracking.smoothing import smooth
from apps.drivers.redis import (
    update_driver_location,
    get_driver_last_point,
    set_driver_last_point,
)


class DriverLocationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("[LocationSocket] Rejecting: Unauthenticated user")
            await self.close(code=4001)
            return

        driver = await self._get_driver(user)
        if not driver:
            logger.warning(f"[LocationSocket] Rejecting: User {user.id} has no driver profile")
            await self.close(code=4003)
            return

        self.driver = driver
        self.last_seq = -1
        self.prev_point = None
        self.last_ping_ts = None  # ⏱️ Track time between pings for speed/waiting logic
        self.last_deviation_alert_ts = 0  # 🚨 Rate limit deviation alerts

        await self.accept()
        logger.info(f"[LocationSocket] ✅ Connected: Driver {driver.id}")

        # 🚀 BROADCAST ON CONNECT (Task 3)
        if self.driver.last_lat and self.driver.last_lng:
            ride = await self._get_active_ride()
            admin_data = {
                "driver_id": self.driver.id,
                "name":      self.driver.user.get_full_name() or self.driver.user.username,
                "phone":     self.driver.user.phone or "",
                "lat": float(self.driver.last_lat),
                "lng": float(self.driver.last_lng),
                "status": self.driver.status,
                "ts": int(time.time()),
            }
            if ride:
                admin_data["ride"] = {
                    "id": ride.id,
                    "status": ride.status,
                    "pickup":  {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
                    "pickup_address": ride.pickup_address or "",
                    "dropoff": {"lat": float(ride.drop_lat),  "lng": float(ride.drop_lng)},
                    "drop_address": ride.drop_address or "",
                    "polyline": ride.planned_route_polyline,
                    "rider_id": ride.rider_id,
                    "rider_name": ride.rider.get_full_name() or ride.rider.username,
                    "vehicle_type": ride.vehicle_type,
                }

            await self.channel_layer.group_send(
                "admin_live_map",
                {"type": "driver_location_updated", "data": admin_data},
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        seq = data.get("seq")

        if seq is None or seq <= self.last_seq:
            return

        self.last_seq = seq

        raw_lat, raw_lng = float(data["lat"]), float(data["lng"])
        accuracy_m = data.get("accuracy_m")
        
        # 🚫 1. Reject noisy GPS pings BEFORE processing (relaxed for indoor testing)
        if accuracy_m is not None and float(accuracy_m) > 120:
            logger.warning(f"[LocationSocket] Dropping noisy ping ({accuracy_m}m): Driver {self.driver.id}")
            # Still update heartbeat in Redis so they don't appear OFFLINE
            from django.utils import timezone
            await database_sync_to_async(update_driver_location)(
                self.driver.id, raw_lat, raw_lng,
            )
            return

        # 🚀 2. Road Snapping (Google Roads API) - only on clean data
        from django.conf import settings
        from apps.tracking.geo import snap_to_roads
        final_lat, final_lng = snap_to_roads(raw_lat, raw_lng, api_key=settings.GOOGLE_MAPS_API_KEY)
        
        heading = data.get("heading")
        speed_kmh = data.get("speed_kmh")

        # � 3. Update Redis (Real-time, extremely fast)
        await database_sync_to_async(update_driver_location)(
            self.driver.id, final_lat, final_lng,
        )
        
        # 🐘 4. Throttled DB update (PostgreSQL) — every 10 pings to save IO
        if seq % 10 == 0:
            def _update_db():
                from apps.drivers.models import Driver
                from django.utils import timezone
                Driver.objects.filter(id=self.driver.id).update(
                    last_lat=final_lat, 
                    last_lng=final_lng,
                    updated_at=timezone.now()
                )
                # Refresh status from DB (it might have changed server-side)
                self.driver.refresh_from_db(fields=["status"])
            await database_sync_to_async(_update_db)()

        # 2️⃣ Get active ride
        ride = await self._get_active_ride()

        if ride:
            deviation_m = None
            if ride.planned_route_polyline:
                route = decode_route(ride.planned_route_polyline)
                snapped, deviation_m = snap_to_route(final_lat, final_lng, route)

                if not is_deviated(deviation_m):
                    smooth_point = smooth(self.prev_point, snapped)
                    self.prev_point = smooth_point
                    final_lat, final_lng = smooth_point
                else:
                    # 🚨 Driver is off-route — alert admin (Rate limited to 30s)
                    now = time.time()
                    if now - self.last_deviation_alert_ts > 30:
                        self.last_deviation_alert_ts = now
                        logger.warning(
                            f"[LocationSocket] Driver {self.driver.id} deviated {deviation_m:.0f}m from route"
                        )
                        await self.channel_layer.group_send(
                            "admin_live_map",
                            {
                                "type": "route_deviation_alert",
                                "data": {
                                    "driver_id": self.driver.id,
                                    "driver_name": self.driver.user.get_full_name() or self.driver.user.username,
                                    "ride_id": ride.id,
                                    "deviation_m": round(deviation_m, 1),
                                    "lat": final_lat,
                                    "lng": final_lng,
                                    "ts": int(now),
                                },
                            },
                        )

            # 3️⃣ Accumulate actual distance & route polyline during trip
            if ride.status == Ride.Status.ONGOING:
                now_ts = time.time()
                elapsed_seconds = (now_ts - self.last_ping_ts) if self.last_ping_ts else 0
                self.last_ping_ts = now_ts

                prev = await database_sync_to_async(get_driver_last_point)(self.driver.id)
                delta_km = accumulate_distance(prev, (final_lat, final_lng))
                
                # ── Waiting Detector (New) ───────────────────────────────────
                from apps.rides.services.waiting_detector import process_location_update
                if prev:
                    wait_data = await database_sync_to_async(process_location_update)(
                        ride_id=ride.id,
                        lat=final_lat,
                        lng=final_lng,
                        prev_lat=prev[0],
                        prev_lng=prev[1],
                        elapsed_seconds=elapsed_seconds
                    )
                    # If state changed, we could broadcast it, but for now we just 
                    # let it accumulate in Redis until ride completion.
                # ──────────────────────────────────────────────────────────────

                def _update_ride_history():
                    import polyline
                    # 1. Update distance
                    if delta_km > 0:
                        ride.actual_distance_km += delta_km
                    
                    # 2. Append to actual route polyline
                    existing_path = []
                    if ride.actual_route_polyline:
                        existing_path = polyline.decode(ride.actual_route_polyline)
                    
                    existing_path.append((final_lat, final_lng))
                    ride.actual_route_polyline = polyline.encode(existing_path)
                    
                    ride.save(update_fields=["actual_distance_km", "actual_route_polyline"])
                
                await database_sync_to_async(_update_ride_history)()
                
                await database_sync_to_async(set_driver_last_point)(
                    self.driver.id, final_lat, final_lng
                )
            else:
                # Still track timestamp even if ride not ONGOING (for pickup waiting)
                self.last_ping_ts = time.time()

        # 4️⃣ Calculate simple ETA
        eta_min = None
        if ride:
            # If driver is on the way to pickup or has arrived but trip hasn't started
            if ride.status in [Ride.Status.ASSIGNED, Ride.Status.ARRIVED]:
                dest_lat = ride.pickup_lat
                dest_lng = ride.pickup_lng
            else:
                # Trip has started (ONGOING)
                dest_lat = ride.drop_lat
                dest_lng = ride.drop_lng
            
            from apps.tracking.geo import haversine_m
            dist_m = haversine_m(final_lat, final_lng, dest_lat, dest_lng)
            # Estimate 25 km/h = 0.41 km/min
            eta_min = int(max(1, (dist_m / 1000.0) / 0.41))

        # 5️⃣ Broadcast to admin live map
        admin_data = {
            "driver_id": self.driver.id,
            "name":      self.driver.user.get_full_name() or self.driver.user.username,
            "phone":     self.driver.user.phone or "",
            "lat": final_lat,
            "lng": final_lng,
            "heading": heading,
            "speed_kmh": round(float(speed_kmh), 1) if speed_kmh is not None else None,
            "status": self.driver.status,
            "eta": eta_min,
            "ts": int(time.time()),
        }
        if ride:
            admin_data["ride"] = {
                "id": ride.id,
                "status": ride.status,
                "pickup":  {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
                "pickup_address": ride.pickup_address or "",
                "dropoff": {"lat": float(ride.drop_lat),  "lng": float(ride.drop_lng)},
                "drop_address": ride.drop_address or "",
                "polyline": ride.planned_route_polyline,
                "rider_id": ride.rider_id,
                "rider_name": ride.rider.get_full_name() or ride.rider.username,
                "distance_km": round(float(ride.actual_distance_km), 2),
                "vehicle_type": ride.vehicle_type,
            }

        await self.channel_layer.group_send(
            "admin_live_map",
            {"type": "driver_location_updated", "data": admin_data},
        )

        # 6️⃣ Broadcast to rider group
        if ride:
            await self.channel_layer.group_send(
                f"ride_{ride.id}",
                {
                    "type": "location_update",
                    "lat": final_lat,
                    "lng": final_lng,
                    "heading": heading,
                    "eta": eta_min,
                    "ts": int(time.time()),
                },
            )

        # 7️⃣ Sync back to Driver (Echo)
        await self.send(text_data=json.dumps({
            "type": "location_sync",
            "lat": final_lat,
            "lng": final_lng,
            "heading": heading,
            "eta": eta_min
        }))

    async def disconnect(self, code):
        """Notify admin live map so the driver marker can be removed."""
        if hasattr(self, "driver"):
            await self.channel_layer.group_send(
                "admin_live_map",
                {
                    "type": "driver_location_updated",
                    "data": {
                        "driver_id": self.driver.id,
                        "offline": True,       # signal to remove from map
                        "status": "OFFLINE",
                        "lat": float(self.driver.last_lat) if self.driver.last_lat else 0,
                        "lng": float(self.driver.last_lng) if self.driver.last_lng else 0,
                        "ts": int(time.time()),
                    },
                },
            )

    @database_sync_to_async
    def _get_driver(self, user):
        try:
            from apps.drivers.models import Driver
            return Driver.objects.select_related("user").get(user=user)
        except Exception:
            return None

    @database_sync_to_async
    def _get_active_ride(self):
        return Ride.objects.filter(
            driver=self.driver,
            status__in=[
                Ride.Status.OFFERED,
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).select_related("rider").first()