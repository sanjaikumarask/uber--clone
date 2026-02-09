# apps/tracking/consumers/rider_tracking.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.rides.models import Ride


class RiderTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        self.ride_id = self.scope["url_route"]["kwargs"]["ride_id"]

        if not user.is_authenticated:
            await self.close()
            return

        self.is_authorized = await self._validate_ride(user)
        if not self.is_authorized:
            await self.close()
            return

        self.group_name = f"ride_{self.ride_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def location_update(self, event):
        if not await self._is_ride_active():
            await self.close()
            return

        await self.send(text_data=json.dumps({
            "lat": event["lat"],
            "lng": event["lng"],
            "eta": event.get("eta"),
            "ts": event["ts"],
        }))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    @database_sync_to_async
    def _validate_ride(self, user):
        return Ride.objects.filter(
            id=self.ride_id,
            rider=user,
            status__in=[
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).exists()

    @database_sync_to_async
    def _is_ride_active(self):
        return Ride.objects.filter(
            id=self.ride_id,
            status__in=[Ride.Status.ARRIVED, Ride.Status.ONGOING],
        ).exists()
