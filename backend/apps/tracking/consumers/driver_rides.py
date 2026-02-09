import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.rides.models import Ride
from apps.rides.services.otp import generate_and_attach_otp


class DriverRideConsumer(AsyncWebsocketConsumer):
    """
    Driver ↔ Server
    - Accept ride (implicit)
    - Mark arrived
    """

    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated or not hasattr(user, "driver"):
            await self.close()
            return

        self.driver = user.driver
        self.group_name = f"driver_{self.driver.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        ride_id = data.get("ride_id")

        if action == "MARK_ARRIVED":
            await self._mark_arrived(ride_id)

    @database_sync_to_async
    def _mark_arrived(self, ride_id):
        with transaction.atomic():
            ride = Ride.objects.select_for_update().get(id=ride_id)

            if ride.driver_id != self.driver.id:
                return

            if ride.status != Ride.Status.ASSIGNED:
                return

            ride.arrived_at = timezone.now()
            ride.transition_to(Ride.Status.ARRIVED)
            generate_and_attach_otp(ride)
