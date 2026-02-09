import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.rides.models import Ride

logger = logging.getLogger(__name__)


class RideConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            user = self.scope.get("user")

            # 🔒 Auth check
            if not user or not user.is_authenticated:
                logger.warning("WS rejected: unauthenticated")
                await self.close()
                return

            # 🔒 Parse + normalize ride_id
            self.ride_id = int(self.scope["url_route"]["kwargs"]["ride_id"])
            self.group_name = f"ride_{self.ride_id}"

            # 🔒 Authorization check
            allowed = await self.user_can_access_ride(user, self.ride_id)
            if not allowed:
                logger.warning(
                    "WS rejected: user=%s not allowed for ride=%s",
                    user.id,
                    self.ride_id,
                )
                await self.close()
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

        except Exception:
            # 🔥 NEVER let connect crash silently
            logger.exception("WS connect crashed")
            await self.close()

    async def disconnect(self, close_code):
        try:
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
        except Exception:
            logger.exception("WS disconnect crashed")

    async def ride_update(self, event):
        """
        Event shape:
        {
            "type": "ride.update",
            "data": {...}
        }
        """
        await self.send_json(event["data"])

    # ============================
    # AUTHORIZATION
    # ============================
    @database_sync_to_async
    def user_can_access_ride(self, user, ride_id) -> bool:
        return Ride.objects.filter(
            id=ride_id,
            rider=user,
        ).exists()
