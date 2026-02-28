# apps/tracking/consumers/rider_tracking.py

import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.rides.models import Ride
from apps.drivers.redis_rider import update_rider_location, get_rider_last_point


class RiderTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]
        self.ride_id = int(self.scope["url_route"]["kwargs"]["ride_id"])

        # Group for all participants of this ride (driver, rider, admin)
        self.group_name = f"ride_{self.ride_id}"
        # User-specific group — used to evict duplicate connections from same user
        self.user_group = f"ride_{self.ride_id}_user_{user.id}"

        if not user.is_authenticated:
            await self.close()
            return

        # Allow Admins to connect without being the 'rider' of this ride
        self.is_admin = user.is_staff or user.is_superuser
        if not self.is_admin:
            if not await self._validate_ride(user):
                await self.close()
                return

        # ── Evict any previous consumer for this (user, ride) pair ──
        # This prevents RIDE_COMPLETED being sent multiple times when the
        # client reconnects and there are multiple consumer instances alive.
        await self.channel_layer.group_send(
            self.user_group,
            {"type": "consumer_evicted"}
        )
        # Now join both groups
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        # 🚀 Send initial snapshot so UI updates immediately
        ride = await self._get_ride_with_driver()
        if ride:
            payload = {
                "ride": {
                    "id": ride.id,
                    "status": ride.status,
                    "otp_code": ride.otp_code,
                    "polyline": ride.planned_route_polyline,
                    "pickup_lat": float(ride.pickup_lat),
                    "pickup_lng": float(ride.pickup_lng),
                    "drop_lat": float(ride.drop_lat),
                    "drop_lng": float(ride.drop_lng),
                    "driver": None
                }
            }
            if ride.driver:
                payload["ride"]["driver"] = {
                    "id": ride.driver.id,
                    "lat": float(ride.driver.last_lat) if ride.driver.last_lat else None,
                    "lng": float(ride.driver.last_lng) if ride.driver.last_lng else None,
                    "status": ride.driver.status,
                }
            
            # Send last known Rider location if available
            rider_loc = get_rider_last_point(ride.rider_id)
            if rider_loc:
                payload["ride"]["rider_loc"] = {"lat": rider_loc[0], "lng": rider_loc[1]}


            await self.send(text_data=json.dumps({
                "type": "WS_CONNECTED",
                "payload": payload
            }))

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        Mainly for receiving RIDER location updates.
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "SEND_CHAT":
                message = data.get("message")
                if message:
                    user = self.scope["user"]
                    # Broadcast to ride group
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "new_chat_message",
                            "message": message,
                            "sender_id": user.id,
                            "created_at": int(time.time()),
                        }
                    )

            elif msg_type == "LOCATION_UPDATE":
                payload = data.get("payload", {})
                lat = payload.get("lat")
                lng = payload.get("lng")
                
                if lat and lng:
                    # 1. Update Redis (Rider Location)
                    # We need rider ID. For admin, this is weird, but Admins shouldn't send location.
                    # Normal riders are self.scope["user"]
                    if not self.is_admin:
                        rider_id = self.scope["user"].id
                        update_rider_location(rider_id, lat, lng)
                        
                        # 2. Broadcast to Ride Group (so Admin sees it)
                        await self.channel_layer.group_send(
                            self.group_name,
                            {
                                "type": "rider_location_updated",
                                "lat": lat,
                                "lng": lng,
                                "rider_id": rider_id,
                                "ts": int(time.time()),
                            }
                        )
                        
                        # 3. Broadcast to Admin Global Map
                        # Show Rider on Admin Map if Ride is active (ASSIGNED, ARRIVED, or ONGOING)
                        is_active = await database_sync_to_async(
                            lambda: Ride.objects.filter(
                                id=self.ride_id, 
                                status__in=[
                                    Ride.Status.SEARCHING,
                                    Ride.Status.OFFERED,
                                    Ride.Status.ASSIGNED, 
                                    Ride.Status.ARRIVED, 
                                    Ride.Status.ONGOING
                                ]
                            ).exists()
                        )()

                        if is_active:
                            await self.channel_layer.group_send(
                                "admin_live_map",
                                {
                                    "type": "rider_location_updated",
                                    "data": {
                                        "ride_id": self.ride_id,
                                        "rider_id": rider_id,
                                        "lat": lat,
                                        "lng": lng,
                                        "ts": int(time.time()),
                                    }
                                }
                            )

        except Exception as e:
            print(f"Error processing receive: {e}")

    @database_sync_to_async
    def _get_ride_with_driver(self):
        return Ride.objects.select_related('driver').filter(id=self.ride_id).first()

    # -------------------------------------------------
    # Handler: driver location broadcast
    # DriverLocationConsumer sends type="location_update"
    # simulate_tracking.py sends type="driver_location_updated"
    # Both must be handled here.
    # -------------------------------------------------
    async def location_update(self, event):
        """Alias: DriverLocationConsumer sends 'location_update'"""
        await self.driver_location_updated(event)

    async def driver_location_updated(self, event):
        """Forward GPS ping to the connected rider (or admin)."""
        # Forward to connected client (Rider or Admin)
        await self.send(text_data=json.dumps({
            "type": "DRIVER_LOCATION_UPDATED",
            "payload": {
                "lat": event["lat"],
                "lng": event["lng"],
                "heading": event.get("heading"),
                "eta": event.get("eta"),
                "ts":  event.get("ts"),
            }
        }))

    # -------------------------------------------------
    # Handler: rider location broadcast
    # type = "rider_location_update"
    # -------------------------------------------------
    async def rider_location_updated(self, event):
        # Admin listening on this socket needs to see it. 
        # The Rider sending it doesn't need echo, but it's simpler to broadcast to all.
        await self.send(text_data=json.dumps({
            "type": "RIDER_LOCATION_UPDATED",
            "payload": {
                "lat": event["lat"],
                "lng": event["lng"],
                "rider_id": event.get("rider_id"),
                "ts": event["ts"],
            }
        }))

    # -------------------------------------------------
    # Handler: ride completed broadcast
    # type = "ride_completed"
    # -------------------------------------------------
    async def ride_completed(self, event):
        try:
            # Only attempt send if the connection hasn't been closed by the underlying protocol
            await self.send(text_data=json.dumps({
                "type": "RIDE_COMPLETED",
                "payload": {
                    "ride_id": event.get("ride_id"),
                    "fare": event.get("fare"),
                }
            }))
        except Exception:
            pass # Socket already closed
        
        await self.close()

    async def new_chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "NEW_CHAT_MESSAGE",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "created_at": event["created_at"],
        }))

    # -------------------------------------------------
    # Handler: generic ride update
    # type = "ride_update"
    # -------------------------------------------------
    async def ride_update(self, event):
        data = event.get("data", {})
        ride_data = data.get("ride", {})
        
        await self.send(text_data=json.dumps({
            "type": "RIDE_STATUS_UPDATED",
            "payload": {
                "status": ride_data.get("status"),
                "otp_code": ride_data.get("otp_code"),
                "polyline": ride_data.get("planned_route_polyline"),
                "driver": ride_data.get("driver"),
            }
        }))

    # -------------------------------------------------
    # Handler: ride status changes
    # type = "ride_status_update"
    # -------------------------------------------------
    async def ride_status_update(self, event):
        ride = await self._get_ride_with_driver()
        if not ride:
            return

        # COMPLETED is handled exclusively by the ride_completed handler.
        # Skip here to avoid double-navigation on the frontend.
        if ride.status == "COMPLETED":
            return

        await self.send(text_data=json.dumps({
            "type": "RIDE_STATUS_UPDATED",
            "payload": {
                "status": ride.status,
                "otp_code": ride.otp_code,
                "polyline": ride.planned_route_polyline,
                "driver": {
                    "id": ride.driver.id if ride.driver else None,
                    "lat": float(ride.driver.last_lat) if (ride.driver and ride.driver.last_lat) else None,
                    "lng": float(ride.driver.last_lng) if (ride.driver and ride.driver.last_lng) else None,
                    "status": ride.driver.status if ride.driver else None,
                }
            }
        }))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    # Handler: evict old consumers when a new connection replaces this one
    async def consumer_evicted(self, event):
        """Called on the old consumer when a new one takes over. Close silently."""
        # code=4001 → client socket.onclose guard won't reconnect
        await self.close(code=4001)

    # -------------------------------------------------
    # DB helpers
    # -------------------------------------------------

    @database_sync_to_async
    def _validate_ride(self, user):
        """Allow connection for any non-terminal ride status."""
        from django.db.models import Q
        return Ride.objects.filter(
            Q(rider=user) | Q(driver__user=user),
            id=self.ride_id,
        ).exclude(
            status__in=[Ride.Status.CANCELLED]
        ).exists()

    @database_sync_to_async
    def _is_ride_active(self):
        return Ride.objects.filter(
            id=self.ride_id,
        ).exclude(
            status__in=[Ride.Status.CANCELLED]
        ).exists()