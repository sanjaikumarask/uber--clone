import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db import models

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
        payload = {"ride": ride_data}
        logger.info(
            f"Sending WS_CONNECTED for ride {self.ride_id} with payload: {payload}"
        )
        await self.send_json(
            {
                "type": "WS_CONNECTED",
                "ride_id": self.ride_id,
                "payload": payload,
            }
        )

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
        """Standard location update or generic event"""
        message = {
            "type": event.get("event", "RIDE_EVENT"),
            "ride_id": self.ride_id,
            "payload": event.get("data", {}),
        }
        await self.send_json(message)

    async def location_update(self, event):
        """Handle GPS pings from DriverLocationConsumer"""
        await self.send_json(
            {
                "type": "DRIVER_LOCATION_UPDATED",
                "ride_id": self.ride_id,
                "payload": {
                    "lat": event.get("lat"),
                    "lng": event.get("lng"),
                    "heading": event.get("heading"),
                    "eta": event.get("eta"),
                    "ts": event.get("ts"),
                },
            }
        )

    async def driver_location_updated(self, event):
        """Alias for simulator consistency"""
        await self.location_update(event)

    async def ride_completed(self, event):
        """Specifically handle ride completion"""
        await self.send_json(
            {
                "type": "RIDE_COMPLETED",
                "ride_id": self.ride_id,
                "payload": {
                    "fare": event.get("fare"),
                },
            }
        )

    async def ride_status_update(self, event):
        """Specifically handle status changes (ARRIVED, ONGOING, etc.)"""
        # Event might already contain the ride data (from simulate_tracking)
        # or we might need to fetch it (from Production lifecycle)
        ride_data = event.get("data")
        if not ride_data:
            ride_data = await self.get_ride_data(self.ride_id)

        await self.send_json(
            {
                "type": "RIDE_STATUS_UPDATED",
                "ride_id": self.ride_id,
                "payload": ride_data,
            }
        )

    # ======================================================
    # INCOMING MESSAGES (CHAT)
    # ======================================================
    async def receive_json(self, content, **kwargs):
        """Handle incoming messages from CLIENT (Rider or Driver)"""
        msg_type = content.get("type")
        user = self.scope["user"]

        if msg_type == "LOCATION_UPDATE":
            payload = content.get("payload", {})
            lat = payload.get("lat")
            lng = payload.get("lng")
            if lat is not None and lng is not None:
                # Broadcast to admin live map
                await self.channel_layer.group_send(
                    "admin_live_map",
                    {
                        "type": "rider_location_updated",
                        "data": {
                            "rider_id": user.id,
                            "rider_name": user.get_full_name() or user.username,
                            "lat": lat,
                            "lng": lng,
                            "ts": int(time.time()),
                        },
                    },
                )
            return

        if msg_type == "SEND_CHAT":
            message_text = content.get("message")
            if not message_text:
                return

            # Save to DB
            msg_obj = await self.save_chat_message(user, self.ride_id, message_text)

            # Broadcast to group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "sender_id": user.id,
                    "message": message_text,
                    "created_at": str(msg_obj.created_at),
                },
            )

    async def chat_message(self, event):
        """Handler for 'chat_message' group event"""
        await self.send_json(
            {
                "type": "NEW_CHAT_MESSAGE",
                "ride_id": self.ride_id,
                "payload": {
                    "sender_id": event["sender_id"],
                    "message": event["message"],
                    "created_at": event["created_at"],
                },
            }
        )

    # ======================================================
    # HELPERS
    # ======================================================
    @database_sync_to_async
    def save_chat_message(self, user, ride_id, text):
        from .models import ChatMessage

        return ChatMessage.objects.create(ride_id=ride_id, sender=user, content=text)

    # ======================================================
    # PERMISSION CHECK
    # ======================================================
    @database_sync_to_async
    def user_can_access_ride(self, user, ride_id: int) -> bool:
        return (
            Ride.objects.filter(id=ride_id)
            .filter(models.Q(rider=user) | models.Q(driver__user=user))
            .exists()
        )

    @database_sync_to_async
    def get_ride_data(self, ride_id: int):
        from .serializers import RideDetailSerializer

        ride = Ride.objects.get(id=ride_id)
        return RideDetailSerializer(ride).data
