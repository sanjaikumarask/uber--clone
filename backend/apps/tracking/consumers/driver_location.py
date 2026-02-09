# apps/tracking/consumers/driver_location.py

import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from apps.rides.models import Ride
from apps.tracking.routing import (
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
        user = self.scope["user"]
        if not user.is_authenticated or not hasattr(user, "driver"):
            await self.close()
            return

        self.driver = user.driver
        self.last_seq = -1
        self.prev_point = None
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        seq = data.get("seq")

        if seq is None or seq <= self.last_seq:
            return
        self.last_seq = seq

        raw = (float(data["lat"]), float(data["lng"]))

        ride = await self._get_active_ride()
        if not ride or not ride.planned_route_polyline:
            return

        route = decode_route(ride.planned_route_polyline)
        snapped, deviation_m = snap_to_route(raw[0], raw[1], route)

        if is_deviated(deviation_m):
            # Phase 4 rule: stop trusting this route
            return

        smooth_point = smooth(self.prev_point, snapped)
        self.prev_point = smooth_point

        prev = await database_sync_to_async(get_driver_last_point)(self.driver.id)
        delta_km = accumulate_distance(prev, smooth_point)

        if delta_km > 0:
            ride.actual_distance_km += delta_km
            await database_sync_to_async(ride.save)(
                update_fields=["actual_distance_km"]
            )

        await database_sync_to_async(set_driver_last_point)(
            self.driver.id,
            smooth_point[0],
            smooth_point[1],
        )

        await database_sync_to_async(update_driver_location)(
            self.driver.id,
            smooth_point[0],
            smooth_point[1],
        )

        await self.channel_layer.group_send(
            f"ride_{ride.id}",
            {
                "type": "location_update",
                "lat": smooth_point[0],
                "lng": smooth_point[1],
                "distance_km": round(ride.actual_distance_km, 3),
                "ts": int(time.time()),
            },
        )

    @database_sync_to_async
    def _get_active_ride(self):
        return Ride.objects.filter(
            driver=self.driver,
            status=Ride.Status.ONGOING,
        ).first()
