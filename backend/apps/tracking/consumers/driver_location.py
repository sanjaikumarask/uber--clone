# apps/tracking/consumers/driver_location.py

import json
import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

from apps.drivers.redis import (
    get_driver_last_point,
    redis_client,
    set_driver_last_point,
    update_driver_location,
)
from apps.rides.models import Ride
from apps.rides.services.realtime import buffer_ride_progress
from apps.tracking.geo import (
    accumulate_distance,
    decode_route,
    is_deviated,
    snap_to_route,
)
from apps.tracking.smoothing import smooth


class DriverLocationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")
        if not await self._authenticate_driver(user):
            return

        # ── BACKPRESSURE: Connection Rate Limiting ──
        from apps.common.backpressure import ConnectionRateLimiter
        if not ConnectionRateLimiter.is_allowed(self.driver.id):
            logger.warning(f"[LocationSocket] 🛑 Rate Limited: Driver {self.driver.id} reconnecting too fast")
            await self.close(code=4029)
            return

        await self._enforce_single_session()
        await self._sync_driver_status_online()
        await self.accept()
        logger.info(f"[LocationSocket] ✅ Connected: Driver {self.driver.id}")
        await self._broadcast_initial_location()

    async def _authenticate_driver(self, user):
        if not user or not user.is_authenticated:
            logger.warning("[LocationSocket] Rejecting: Unauthenticated user")
            await self.close(code=4001)
            return False
        driver = await self._get_driver(user)
        if not driver:
            logger.warning(f"[LocationSocket] Rejecting: User {user.id} has no driver profile")
            await self.close(code=4003)
            return False
        self.driver = driver
        self.last_seq = -1
        self.prev_point = None
        self.last_ping_ts = None
        self.last_deviation_alert_ts = 0
        self.last_admin_broadcast_ts = 0
        return True

    async def _enforce_single_session(self):
        session_key = f"driver_socket:{self.driver.id}"
        old_channel = redis_client.get(session_key)
        if old_channel and old_channel != self.channel_name:
            logger.info(f"[LocationSocket] Evicting old session {old_channel} for Driver {self.driver.id}")
            await self.channel_layer.send(old_channel, {"type": "force_disconnect", "reason": "new_login"})
        redis_client.set(session_key, self.channel_name, ex=3600)

    async def _sync_driver_status_online(self):
        redis_client.set(f"driver:{self.driver.id}:last_seen", int(time.time()), ex=300)
        self.driver = await self._get_driver(self.scope.get("user"))
        if self.driver.status == "OFFLINE":
            def _sync():
                from apps.drivers.models import Driver
                Driver.objects.filter(id=self.driver.id).update(status="ONLINE")
            await database_sync_to_async(_sync)()
            self.driver.status = "ONLINE"

    async def _broadcast_initial_location(self):
        if self.driver.last_lat and self.driver.last_lng:
            ride = await self._get_active_ride()
            admin_data = self._build_broadcast_data(ride, float(self.driver.last_lat), float(self.driver.last_lng), {}, None)
            await self.channel_layer.group_send("admin_live_map", {"type": "driver_location_updated", "data": admin_data})

    async def receive(self, text_data):
        data = json.loads(text_data)
        redis_client.set(f"driver:{self.driver.id}:last_seen", int(time.time()), ex=300)

        if data.get("type") == "ping":
            await self.send(json.dumps({"type": "pong", "ts": int(time.time())}))
            return

        if not self._is_valid_sequence(data.get("seq")):
            return

        raw_lat, raw_lng = float(data["lat"]), float(data["lng"])
        accuracy_m = float(data.get("accuracy_m", 0))

        from apps.tracking.services import LocationProcessor
        if LocationProcessor.filter_noisy_ping(accuracy_m):
            await database_sync_to_async(update_driver_location)(self.driver.id, raw_lat, raw_lng)
            return

        final_lat, final_lng = await LocationProcessor.get_snapped_coords(raw_lat, raw_lng, self.last_seq)
        await self._persist_location(final_lat, final_lng)

        ride = await self._get_active_ride()
        eta_min = await self._process_ride_location(ride, final_lat, final_lng) if ride else None

        await self._broadcast_location(ride, final_lat, final_lng, data, eta_min)
        await self.send(json.dumps({"type": "location_sync", "lat": final_lat, "lng": final_lng, "eta": eta_min}))

    def _is_valid_sequence(self, seq):
        if seq is None or seq <= self.last_seq:
            return False
        self.last_seq = seq
        return True

    async def _persist_location(self, lat, lng):
        await database_sync_to_async(update_driver_location)(self.driver.id, lat, lng)
        if self.last_seq % 10 == 0:
            await self._update_driver_db(lat, lng)

    async def _process_ride_location(self, ride, lat, lng):
        from apps.tracking.services import LocationProcessor
        if ride.planned_route_polyline:
            route = decode_route(ride.planned_route_polyline)
            snapped, deviation_m = snap_to_route(lat, lng, route)
            if not is_deviated(deviation_m):
                lat, lng = smooth(self.prev_point, snapped)
            elif time.time() - self.last_deviation_alert_ts > 30:
                await self._send_deviation_alert(ride, lat, lng, deviation_m)

        if ride.status == Ride.Status.ONGOING:
            now_ts = time.time()
            elapsed = (now_ts - self.last_ping_ts) if self.last_ping_ts else 0
            self.last_ping_ts = now_ts
            prev = await database_sync_to_async(get_driver_last_point)(self.driver.id)
            delta_km = accumulate_distance(prev, (lat, lng))
            if not LocationProcessor.detect_fraud(ride, delta_km, elapsed):
                buffer_ride_progress(ride.id, lat, lng, delta_km)
                await database_sync_to_async(set_driver_last_point)(self.driver.id, lat, lng)

        return LocationProcessor.calculate_eta(ride, lat, lng)

    async def _broadcast_location(self, ride, lat, lng, data, eta_min):
        admin_data = self._build_broadcast_data(ride, lat, lng, data, eta_min)
        await self._throttled_admin_broadcast(admin_data)
        if ride:
            await self._broadcast_to_rider(ride.id, lat, lng, data, eta_min)

    async def _update_driver_db(self, lat, lng):
        from django.utils import timezone

        from apps.drivers.models import Driver

        await database_sync_to_async(Driver.objects.filter(id=self.driver.id).update)(
            last_lat=lat, last_lng=lng, updated_at=timezone.now()
        )

    async def _send_deviation_alert(self, ride, lat, lng, deviation_m):
        self.last_deviation_alert_ts = time.time()
        await self.channel_layer.group_send(
            "admin_live_map",
            {
                "type": "route_deviation_alert",
                "data": {
                    "driver_id": self.driver.id,
                    "ride_id": ride.id,
                    "deviation_m": round(deviation_m, 1),
                    "lat": lat,
                    "lng": lng,
                    "ts": int(time.time()),
                },
            },
        )

    def _build_broadcast_data(self, ride, lat, lng, raw_data, eta_min):
        res = {
            "driver_id": self.driver.id,
            "lat": lat,
            "lng": lng,
            "heading": raw_data.get("heading"),
            "speed_kmh": round(float(raw_data.get("speed_kmh", 0)), 1),
            "status": self.driver.status,
            "eta": eta_min,
            "ts": int(time.time()),
        }
        if ride:
            res["ride"] = {
                "id": ride.id,
                "status": ride.status,
                "pickup_address": ride.pickup_address,
                "drop_address": ride.drop_address,
            }
        return res

    async def _throttled_admin_broadcast(self, data):
        now = time.time()
        if now - self.last_admin_broadcast_ts >= 1.0:
            self.last_admin_broadcast_ts = now
            await self.channel_layer.group_send(
                "admin_live_map", {"type": "driver_location_updated", "data": data}
            )

    async def _broadcast_to_rider(self, ride_id, lat, lng, data, eta_min):
        await self.channel_layer.group_send(
            f"ride_{ride_id}",
            {
                "type": "location_update",
                "lat": lat,
                "lng": lng,
                "heading": data.get("heading"),
                "eta": eta_min,
                "ts": int(time.time()),
            },
        )

    async def force_disconnect(self, event):
        """Forcefully disconnect this socket because a newer one arrived."""
        await self.send(
            json.dumps(
                {
                    "type": "error",
                    "code": "SESSION_EVICTED",
                    "message": "Another connection for this driver was detected. Disconnecting.",
                }
            )
        )
        await self.close(code=4999)

    async def disconnect(self, code):
        """Notify admin live map so the driver marker can be removed."""
        if hasattr(self, "driver"):
            # ── Session Cleanup ──
            from apps.drivers.redis import redis_client

            session_key = f"driver_socket:{self.driver.id}"
            current_channel = redis_client.get(session_key)
            if current_channel == self.channel_name:
                redis_client.delete(session_key)

            await self.channel_layer.group_send(
                "admin_live_map",
                {
                    "type": "driver_location_updated",
                    "data": {
                        "driver_id": self.driver.id,
                        "offline": True,  # signal to remove from map
                        "status": "OFFLINE",
                        "lat": (
                            float(self.driver.last_lat) if self.driver.last_lat else 0
                        ),
                        "lng": (
                            float(self.driver.last_lng) if self.driver.last_lng else 0
                        ),
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
        return (
            Ride.objects.filter(
                driver=self.driver,
                status__in=[
                    Ride.Status.OFFERED,
                    Ride.Status.ASSIGNED,
                    Ride.Status.ARRIVED,
                    Ride.Status.ONGOING,
                ],
            )
            .select_related("rider")
            .first()
        )
