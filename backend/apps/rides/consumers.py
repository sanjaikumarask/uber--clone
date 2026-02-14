import logging
from django.db import models
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from apps.rides.models import Ride

logger = logging.getLogger(__name__)


class RideConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for a single ride.
    Contract:
    - One socket per ride
    - Backend is authoritative
    - Messages are structured and version-safe
    """

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("WS connect rejected: unauthenticated")
            await self.close(code=4001)
            return

        try:
            self.ride_id = int(self.scope["url_route"]["kwargs"]["ride_id"])
        except (KeyError, ValueError):
            logger.warning("WS connect rejected: invalid ride_id")
            await self.close(code=4002)
            return

        self.group_name = f"ride_{self.ride_id}"

        allowed = await self.user_can_access_ride(user, self.ride_id)
        if not allowed:
            logger.warning(
                "WS connect rejected: user=%s ride=%s",
                user.id,
                self.ride_id,
            )
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()
        logger.info(
            "WS connected: user=%s ride=%s",
            user.id,
            self.ride_id,
        )

        # Optional: initial handshake message with current ride state
        ride_data = await self.get_ride_data(self.ride_id)
        await self.send_json({
            "type": "WS_CONNECTED",
            "ride_id": self.ride_id,
            "payload": {
                "ride": ride_data
            },
        })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

        logger.info(
            "WS disconnected: ride=%s code=%s",
            getattr(self, "ride_id", None),
            close_code,
        )

    # ======================================================
    # EVENT HANDLER (CALLED BY group_send)
    # ======================================================
    async def ride_update(self, event):
        """
        Expected event shape from backend:
        {
            "type": "ride_update",
            "event": "RIDE_STATUS_UPDATED",
            "data": {...}
        }
        """

        message = {
            "type": event.get("event", "RIDE_EVENT"),
            "ride_id": self.ride_id,
            "payload": event.get("data", {}),
        }

        await self.send_json(message)

    # ======================================================
    # PERMISSION CHECK
    # ======================================================
    @database_sync_to_async
    def user_can_access_ride(self, user, ride_id: int) -> bool:
        return Ride.objects.filter(
            id=ride_id
        ).filter(
            models.Q(rider=user)
            | models.Q(driver__user=user)
        ).exists()

    @database_sync_to_async
    def get_ride_data(self, ride_id: int):
        from .serializers import RideDetailSerializer
        ride = Ride.objects.get(id=ride_id)
        return RideDetailSerializer(ride).data
