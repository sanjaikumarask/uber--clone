import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

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
            drivers_data = self._fetch_drivers_data()
            riders_data = self._fetch_riders_data()
            return drivers_data, riders_data
        except Exception as e:
            logger.error(
                f"[AdminLiveMap] Error in _get_initial_snapshot: {e}", exc_info=True
            )
            return [], []

    def _fetch_drivers_data(self):
        from apps.drivers.models import Driver
        from apps.rides.models import Ride

        drivers_data = []
        drivers = Driver.objects.filter(
            status__in=["ONLINE", "BUSY", "OFFLINE"],
        ).select_related("user")

        for d in drivers:
            ride = self._get_active_ride_for_driver(d.id)
            lat, lng = self._get_driver_location(d, ride)

            if lat is None or lng is None:
                continue

            if not self._should_include_driver(d):
                continue

            data = self._format_driver_basic_data(d, lat, lng)
            if ride:
                data["ride"] = self._format_ride_snapshot(ride)

            drivers_data.append(data)
        return drivers_data

    def _get_active_ride_for_driver(self, driver_id):
        from apps.rides.models import Ride
        return (
            Ride.objects.filter(
                driver_id=driver_id,
                status__in=[
                    Ride.Status.SEARCHING,
                    Ride.Status.OFFERED,
                    Ride.Status.ASSIGNED,
                    Ride.Status.ARRIVED,
                    Ride.Status.ONGOING,
                ],
            )
            .order_by("-updated_at")
            .first()
        )

    def _get_driver_location(self, driver, ride):
        from apps.drivers.redis import get_driver_last_point
        lat, lng = driver.last_lat, driver.last_lng
        redis_loc = get_driver_last_point(driver.id)
        if redis_loc:
            lat, lng = redis_loc
        elif (lat is None or lng is None) and ride:
            lat, lng = float(ride.pickup_lat), float(ride.pickup_lng)
        return lat, lng

    def _should_include_driver(self, driver):
        # ONLINE or BUSY drivers are always shown.
        # OFFLINE only if they have a non-null last position.
        return driver.status in ["ONLINE", "BUSY"] or (
            driver.status == "OFFLINE" and driver.last_lat
        )

    def _format_driver_basic_data(self, driver, lat, lng):
        return {
            "driver_id": driver.id,
            "name": driver.user.get_full_name() or driver.user.username,
            "phone": driver.user.phone or "",
            "lat": float(lat),
            "lng": float(lng),
            "status": driver.status,
            "ts": int(driver.updated_at.timestamp()) if driver.updated_at else 0,
        }

    def _format_ride_snapshot(self, ride):
        from apps.payments.models import Payment
        payment = Payment.objects.filter(
            ride_id=ride.id, status=Payment.Status.CAPTURED
        ).first()

        return {
            "id": ride.id,
            "status": ride.status,
            "payment_status": payment.status if payment else None,
            "base_fare": str(ride.base_fare),
            "final_fare": str(ride.final_fare) if ride.final_fare else None,
            "pickup": {
                "lat": float(ride.pickup_lat),
                "lng": float(ride.pickup_lng),
            },
            "pickup_address": ride.pickup_address or "",
            "dropoff": {
                "lat": float(ride.drop_lat),
                "lng": float(ride.drop_lng),
            },
            "drop_address": ride.drop_address or "",
            "polyline": ride.planned_route_polyline,
            "rider_id": ride.rider_id,
            "rider_name": ride.rider.get_full_name() or ride.rider.username,
            "distance_km": round(float(ride.actual_distance_km), 2),
            "vehicle_type": ride.vehicle_type,
        }

    def _fetch_riders_data(self):
        import time

        from apps.drivers.redis_rider import get_rider_last_point
        from apps.rides.models import Ride

        riders_data = []
        active_rides = Ride.objects.filter(
            status__in=[
                Ride.Status.SEARCHING,
                Ride.Status.OFFERED,
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ]
        ).select_related("rider")

        curr_ts = int(time.time())
        for r in active_rides:
            loc = get_rider_last_point(r.rider_id)
            lat = loc[0] if loc else float(r.pickup_lat)
            lng = loc[1] if loc else float(r.pickup_lng)

            riders_data.append(
                {
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
                        "payment_status": getattr(r, "payment_status", None),
                        "base_fare": str(r.base_fare),
                        "pickup": {
                            "lat": float(r.pickup_lat),
                            "lng": float(r.pickup_lng),
                        },
                        "dropoff": {"lat": float(r.drop_lat), "lng": float(r.drop_lng)},
                        "polyline": r.planned_route_polyline,
                        "vehicle_type": r.vehicle_type,
                    },
                }
            )
        return riders_data

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
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "DRIVER_LOCATION_UPDATED",
                        "data": data,
                    }
                )
            )

        for data in riders_data:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "RIDER_LOCATION_UPDATED",
                        "data": data,
                    }
                )
            )

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
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "DRIVER_LOCATION_UPDATED",
                        "data": data,
                    }
                )
            )

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
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "RIDER_LOCATION_UPDATED",
                        "data": data,
                    }
                )
            )

    # Alias for simulators
    async def rider_location_update(self, event):
        await self.rider_location_updated(event)

    async def admin_generic_event(self, event):
        """Generic events: ride status changes, etc."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": event.get("event", "GENERIC_EVENT"),
                    "data": event.get("data", {}),
                }
            )
        )

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
        await self.send(
            text_data=json.dumps(
                {
                    "type": "ROUTE_DEVIATION",
                    "data": data,
                }
            )
        )
