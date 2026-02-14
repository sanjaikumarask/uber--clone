import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

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
        final_lat, final_lng = raw
        
        # 1. Update Redis (Always - for 'Nearby Drivers')
        await database_sync_to_async(update_driver_location)(
            self.driver.id,
            final_lat,
            final_lng,
        )

        # 2. Check Active Ride (For Snapping & Distance)
        ride = await self._get_active_ride()
        
        if ride and ride.planned_route_polyline:
            route = decode_route(ride.planned_route_polyline)
            snapped, deviation_m = snap_to_route(raw[0], raw[1], route)

            if not is_deviated(deviation_m):
                smooth_point = smooth(self.prev_point, snapped)
                self.prev_point = smooth_point
                final_lat, final_lng = smooth_point

                # Calculate Distance for Fare
                prev = await database_sync_to_async(get_driver_last_point)(self.driver.id)
                delta_km = accumulate_distance(prev, smooth_point)

                if delta_km > 0:
                    ride.actual_distance_km += delta_km
                    await database_sync_to_async(ride.save)(
                        update_fields=["actual_distance_km"]
                    )

                # Update Redis with Snapped Coords
                await database_sync_to_async(set_driver_last_point)(
                    self.driver.id,
                    final_lat,
                    final_lng,
                )
                
                # Broadcast to Rider
                await self.channel_layer.group_send(
                    f"ride_{ride.id}",
                    {
                        "type": "location_update",
                        "lat": final_lat,
                        "lng": final_lng,
                        "distance_km": round(ride.actual_distance_km, 3),
                        "ts": int(time.time()),
                    },
                )

        # 3. Broadcast to Admin Map (Using Final/Snapped or Raw)
        await self.channel_layer.group_send(
            "admin_live_map",
            {
                "type": "driver_location_update",
                "data": {
                    "driver_id": self.driver.id,
                    "lat": final_lat,
                    "lng": final_lng,
                    "status": self.driver.status,
                    "ts": int(time.time()),
                },
            },
        )

    @database_sync_to_async
    def _get_active_ride(self):
        return Ride.objects.filter(
            driver=self.driver,
            status=Ride.Status.ONGOING,
        ).first()
