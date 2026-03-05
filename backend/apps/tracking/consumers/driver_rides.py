# apps/tracking/consumers/driver_rides.py
#
# This consumer is connected by the driver app to receive incoming ride offers
# and ride status events. The matching service (or offer service) sends ride
# offers to the driver's personal channel group via:
#
#   channel_layer.group_send(f"driver_{driver_id}_rides", {
#       "type": "ride_offer",
#       "data": { ride_id, pickup, dropoff, fare, ... }
#   })
#
# This consumer joins that group on connect and forwards events to the app.

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class DriverRidesConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        driver = await self._get_driver(user)
        if not driver:
            await self.close(code=4003)
            return

        self.driver = driver
        # Personal channel group for ride events
        self.rides_group = f"driver_{driver.id}_rides"
        # User notification group
        self.user_group = f"user_{user.id}"

        await self.channel_layer.group_add(self.rides_group, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        
        # ── HEARTBEAT & STATUS SYNC (NEW) ──
        # Standardize with LocationSocket to prevent discovery gaps
        from apps.drivers.redis import redis_client
        import time
        heartbeat_key = f"driver:{driver.id}:last_seen"
        redis_client.set(heartbeat_key, int(time.time()), ex=300)
        
        if driver.status == "OFFLINE":
             def _sync_status():
                 from apps.drivers.models import Driver
                 Driver.objects.filter(id=driver.id).update(status="ONLINE")
             await database_sync_to_async(_sync_status)()
             driver.status = "ONLINE"

        await self.accept()

        logger.info("DriverRidesConsumer connected: driver=%s user=%s", driver.id, user.id)
        
        pending_offer = await self._get_pending_offer(driver)
        if pending_offer:
            logger.info("Found pending offer for driver %s: ride %s", driver.id, pending_offer.id)
            
            # Use same structure as matching service
            from apps.drivers.models import DriverStats
            stats, _ = await database_sync_to_async(DriverStats.objects.get_or_create)(driver=driver)
            
            await self.send(text_data=json.dumps({
                "type": "ride_offer",
                "data": {
                    "ride_id": pending_offer.id,
                    "pickup": {
                        "lat": float(pending_offer.pickup_lat),
                        "lng": float(pending_offer.pickup_lng),
                    },
                    "drop": {
                        "lat": float(pending_offer.drop_lat),
                        "lng": float(pending_offer.drop_lng),
                    },
                    "pickup_address": pending_offer.pickup_address or "",
                    "drop_address":   pending_offer.drop_address or "",
                    "fare_estimate": float(pending_offer.base_fare),
                    "timeout": 60,
                    "is_auto_assigned": False, # If they reconnect, it's usually an offer
                    "rejection_count": stats.rejection_count_today,
                    "rejections_until_auto": max(0, 3 - stats.rejection_count_today),
                    "rider": {
                         "name":   pending_offer.rider.get_full_name() or pending_offer.rider.username,
                         "rating": 5.0 # simplified for reconnect
                    }
                }
            }))

    async def disconnect(self, close_code):
        if hasattr(self, "rides_group"):
            await self.channel_layer.group_discard(self.rides_group, self.channel_name)
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        logger.info(
            "DriverRidesConsumer disconnected: driver=%s code=%s",
            getattr(self, "driver", "unknown"),
            close_code,
        )

    # ── Event handlers (called by channel_layer.group_send) ────────────

    async def ride_offer(self, event):
        """
        Sent by the matching/offer service when a new ride is offered.
        """
        logger.info(f"Forwarding ride_offer to Driver {self.driver.id}: Ride {event.get('data', {}).get('ride_id')}")
        await self.send(text_data=json.dumps({
            "type": "ride_offer",
            "data": event.get("data", {}),
        }))

    async def ride_assigned(self, event):
        """
        Sent when a ride is AUTO-ASSIGNED to a driver.
        """
        logger.info(f"Forwarding ride_assigned to Driver {self.driver.id}: Ride {event.get('data', {}).get('ride_id')}")
        await self.send(text_data=json.dumps({
            "type": "ride_assigned",
            "data": event.get("data", {}),
        }))

    async def ride_cancelled(self, event):
        """
        Sent when a rider cancels before the driver accepts or arrives.
        """
        await self.send(text_data=json.dumps({
            "type": "ride_cancelled",
            "data": event.get("data", {}),
        }))

    async def ride_status_update(self, event):
        """
        Generic status change forwarded to the driver.
        """
        await self.send(text_data=json.dumps(event))

    async def notify(self, event):
        """
        Sent via the Notification system (apps/notifications/providers/websocket.py)
        """
        logger.info(f"Forwarding notification to Driver {self.driver.id}: {event.get('event')}")
        await self.send(text_data=json.dumps({
            "type": event.get("event", "notification"),
            "data": event.get("payload", {}),
        }))

    # ── DB helpers ─────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_driver(self, user):
        try:
            from apps.drivers.models import Driver
            return Driver.objects.select_related("user").get(user_id=user.id)
        except Exception:
            return None

    @database_sync_to_async
    def _get_pending_offer(self, driver):
        from apps.rides.models import Ride
        return Ride.objects.filter(
            driver=driver,
            status=Ride.Status.OFFERED
        ).select_related('rider').first()