import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

GROUP_NAME = "admin_live_map"


class AdminLiveMapConsumer(AsyncWebsocketConsumer):
    """
    Admin Live Map WebSocket Consumer.
    Registered at: ws/admin/live-map/

    Auth: must be an admin (role=ADMIN or is_superuser or is_staff).
    On connect: sends snapshot of all active drivers.
    Listens for: driver_location_update, rider_location_update, admin_generic_event.
    """

    @database_sync_to_async
    def _is_admin_user(self, user) -> bool:
        """Check admin role safely in a thread (DB may be hit for is_admin property)."""
        try:
            return user.is_authenticated and (user.is_admin or user.is_staff)
        except Exception:
            return False

    @database_sync_to_async
    def _get_initial_snapshot(self):
        """Return active driver and rider data for the initial map load."""
        try:
            from apps.drivers.models import Driver
            from apps.rides.models import Ride
            from apps.drivers.redis_rider import get_rider_last_point

            drivers_data = []
            drivers = list(Driver.objects.filter(
                status__in=["ONLINE", "BUSY", "OFFLINE"],
            ).select_related("user"))

            from apps.drivers.redis import get_driver_last_point

            for d in drivers:
                # Find most recent active ride
                ride = Ride.objects.filter(
                    driver_id=d.id,
                    status__in=[
                        Ride.Status.SEARCHING,
                        Ride.Status.OFFERED,
                        Ride.Status.ASSIGNED,
                        Ride.Status.ARRIVED,
                        Ride.Status.ONGOING,
                    ],
                ).order_by("-updated_at").first()

                # Get the best possible coordinate for this driver
                # Priority: Redis (Live) > DB (Cached) > Ride Pickup (Estimation)
                lat = d.last_lat
                lng = d.last_lng
                
                redis_loc = get_driver_last_point(d.id)
                if redis_loc:
                    lat, lng = redis_loc
                
                if (lat is None or lng is None) and ride:
                    lat, lng = float(ride.pickup_lat), float(ride.pickup_lng)
                
                # If we still have no coordinates, they can't be put on a map.
                # But we skip them instead of breaking.
                if lat is None or lng is None:
                    continue

                data = {
                    "driver_id": d.id,
                    "name":   d.user.get_full_name() or d.user.username,
                    "phone":  d.user.phone or "",
                    "lat": float(lat),
                    "lng": float(lng),
                    "status": d.status,
                    "ts": int(d.updated_at.timestamp()) if d.updated_at else 0,
                }

                if ride:
                    from apps.payments.models import Payment
                    payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
                    
                    data["ride"] = {
                        "id": ride.id,
                        "status": ride.status,
                        "payment_status": payment.status if payment else None,
                        "base_fare": str(ride.base_fare),
                        "final_fare": str(ride.final_fare) if ride.final_fare else None,
                        "pickup":  {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
                        "pickup_address": ride.pickup_address or "",
                        "dropoff": {"lat": float(ride.drop_lat),  "lng": float(ride.drop_lng)},
                        "drop_address": ride.drop_address or "",
                        "polyline": ride.planned_route_polyline,
                        "rider_id": ride.rider_id,
                        "rider_name": ride.rider.get_full_name() or ride.rider.username,
                        "distance_km": round(float(ride.actual_distance_km), 2),
                        "vehicle_type": ride.vehicle_type,
                    }
                
                # Inclusion rule: ONLINE or BUSY drivers are always shown. 
                # OFFLINE only if they have a non-null last position.
                if d.status in ["ONLINE", "BUSY"] or (d.status == "OFFLINE" and d.last_lat):
                    drivers_data.append(data)

            # --- RIDERS SNAPSHOT ---
            import time
            riders_data = []
            active_rides = list(Ride.objects.filter(
                status__in=[
                    Ride.Status.SEARCHING,
                    Ride.Status.OFFERED,
                    Ride.Status.ASSIGNED,
                    Ride.Status.ARRIVED,
                    Ride.Status.ONGOING
                ]
            ).select_related("rider"))
            
            curr_ts = int(time.time())
            for r in active_rides:
                # Try to get from Redis
                loc = get_rider_last_point(r.rider_id)
                lat = loc[0] if loc else float(r.pickup_lat)
                lng = loc[1] if loc else float(r.pickup_lng)
                
                data = {
                    "ride_id": r.id,
                    "rider_id": r.rider_id,
                    "rider_name": r.rider.get_full_name() or r.rider.username,
                    "lat": lat,
                    "lng": lng,
                    "status": r.status,
                    "ts": curr_ts,
                    "ride": {
                        "id": r.id,
                        "status": r.status,
                        "payment_status": getattr(r, 'payment_status', None), # Will be null if not joined, but we can't easily join here without more code
                        "base_fare": str(r.base_fare),
                        "pickup": {"lat": float(r.pickup_lat), "lng": float(r.pickup_lng)},
                        "dropoff": {"lat": float(r.drop_lat), "lng": float(r.drop_lng)},
                        "polyline": r.planned_route_polyline,
                        "vehicle_type": r.vehicle_type,
                    }
                }
                riders_data.append(data)

            return drivers_data, riders_data
        except Exception as e:
            logger.error(f"[AdminLiveMap] Error in _get_initial_snapshot: {e}", exc_info=True)
            return [], []

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("[AdminLiveMap] Rejected: unauthenticated")
            await self.close(code=4001)
            return

        is_admin = await self._is_admin_user(user)
        if not is_admin:
            logger.warning(f"[AdminLiveMap] Rejected: user {user.id} is not admin")
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(GROUP_NAME, self.channel_name)
        await self.accept()

        logger.info(f"[AdminLiveMap] ✅ Admin {user.id} connected")

        # Send initial snapshot of active drivers and riders
        drivers_data, riders_data = await self._get_initial_snapshot()
        
        for data in drivers_data:
            await self.send(text_data=json.dumps({
                "type": "DRIVER_LOCATION_UPDATED",
                "data": data,
            }))
        
        for data in riders_data:
            await self.send(text_data=json.dumps({
                "type": "RIDER_LOCATION_UPDATED",
                "data": data,
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(GROUP_NAME, self.channel_name)

    # ── Group event handlers ─────────────────────────────────────────────────
    # These must be lowercase for Channels to route them correctly.

    async def driver_location_updated(self, event):
        """
        Forwarded from DriverLocationConsumer or Simulator.
        """
        data = event.get("data", {})
        if not data:
            # Fallback if structure is flat (legacy simulators)
            data = {k: v for k, v in event.items() if k != "type"}

        if "driver_id" in data:
            # logger.debug(f"[AdminLiveMap] Forwarding move for Driver {data['driver_id']} to ({data.get('lat')}, {data.get('lng')})")
            await self.send(text_data=json.dumps({
                "type": "DRIVER_LOCATION_UPDATED",
                "data": data,
            }))

    # Alias for simulators
    async def driver_location_update(self, event):
        await self.driver_location_updated(event)

    async def location_update(self, event):
        """Alias for Production consumer naming"""
        await self.driver_location_updated(event)

    async def rider_location_updated(self, event):
        """Forwarded from RiderTrackingConsumer or Simulator."""
        data = event.get("data", {})
        if not data:
            data = {k: v for k, v in event.items() if k != "type"}

        if "rider_id" in data:
            # logger.debug(f"[AdminLiveMap] Forwarding move for Rider {data['rider_id']}")
            await self.send(text_data=json.dumps({
                "type": "RIDER_LOCATION_UPDATED",
                "data": data,
            }))

    # Alias for simulators
    async def rider_location_update(self, event):
        await self.rider_location_updated(event)

    async def admin_generic_event(self, event):
        """Generic events: ride status changes, etc."""
        await self.send(text_data=json.dumps({
            "type": event.get("event", "GENERIC_EVENT"),
            "data": event.get("data", {}),
        }))

    async def route_deviation_alert(self, event):
        """
        Fired when a driver strays off the planned route.
        Forwarded to admin frontend as ROUTE_DEVIATION so it can show a warning.
        """
        data = event.get("data", {})
        logger.warning(
            f"[AdminLiveMap] 🚨 ROUTE DEVIATION: Driver {data.get('driver_id')} "
            f"deviated {data.get('deviation_m')}m on Ride {data.get('ride_id')}"
        )
        await self.send(text_data=json.dumps({
            "type": "ROUTE_DEVIATION",
            "data": data,
        }))
