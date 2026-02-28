import logging
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.notifications.models import Notification
from apps.drivers.services.geo import get_nearby_driver_ids
from apps.rides.tasks import driver_accept_timeout

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def find_driver_and_offer_ride(ride_id: int):
    """
    Matching Engine:
    Priority: 1) Level, 2) Score, 3) Distance (preserved via geo order).
    """

    with transaction.atomic():
        ride = Ride.objects.select_for_update().filter(id=ride_id).first()

        if not ride or ride.status != Ride.Status.SEARCHING:
            return

        candidate_ids = get_nearby_driver_ids(
            lat=ride.pickup_lat,
            lng=ride.pickup_lng,
            radius_km=10.0,
            limit=20,  # Fetch more, then sort by level+score
        )

        rejected_ids = set(ride.rejected_driver_ids or [])
        valid_candidate_ids = [d_id for d_id in candidate_ids if d_id not in rejected_ids]

        if not valid_candidate_ids:
            logger.info(f"Ride {ride.id}: No valid drivers.")
            return

        # --- Load candidates from DB with level/score for sorting ---
        LEVEL_PRIORITY = {
            Driver.Level.PRO:        4,
            Driver.Level.CONSISTENT: 3,
            Driver.Level.ACTIVE:     2,
            Driver.Level.NORMAL:     1,
        }

        db_candidates = (
            Driver.objects
            .select_for_update(of=("self",))
            .select_related("user", "stats")
            .filter(
                id__in=valid_candidate_ids,
                status=Driver.Status.ONLINE,
                stats__trust_score__gte=60.0,
                stats__is_suspended=False,
            )
        )

        # Sort: level desc → score desc → preserve geo distance order
        geo_order = {d_id: idx for idx, d_id in enumerate(valid_candidate_ids)}
        sorted_candidates = sorted(
            db_candidates,
            key=lambda d: (
                -LEVEL_PRIORITY.get(d.level, 1),
                -(getattr(d.stats, "score", 0.0) if hasattr(d, "stats") else 0.0),
                geo_order.get(d.id, 999),
            ),
        )

        # Remove stale drivers from geo for any that were ONLINE in Redis but not DB
        db_ids = {d.id for d in sorted_candidates}
        for cid in valid_candidate_ids:
            if cid not in db_ids:
                logger.info(f"Ride {ride.id}: Driver {cid} not ONLINE in DB. Removing from GEO.")
                from apps.drivers.services.geo import remove_driver_from_geo
                remove_driver_from_geo(driver_id=cid)

        driver = sorted_candidates[0] if sorted_candidates else None

        if not driver:
            logger.info(f"Ride {ride.id}: No eligible drivers after sorting.")
            return

        # -----------------------------------------
        # AUTO-ACCEPTANCE LOGIC
        # -----------------------------------------
        from apps.drivers.models import DriverStats
        from apps.drivers.services.metrics import update_driver_metrics
        # stats.check_and_reset_daily_stats() # metrics service handles activity
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        stats.check_and_reset_daily_stats()

        auto_assign = stats.rejection_count_today >= 3  # Penalty: auto-assign after 3 rejections

        # Record that a ride was offered to this driver
        update_driver_metrics(driver, "OFFERED")

        ride.driver = driver
        if auto_assign:
            ride.transition_to(Ride.Status.ASSIGNED)
            driver.status = Driver.Status.BUSY
            driver.save(update_fields=["status"])
            # Auto-assign counts as an accept
            update_driver_metrics(driver, "ACCEPTED")
        else:
            ride.transition_to(Ride.Status.OFFERED)
            # Schedule timeout
            driver_accept_timeout.apply_async((ride.id, driver.id), countdown=60)

        ride.save(update_fields=["driver", "status", "updated_at"])

        def notify():
            # 1. Notify DRIVER
            # If auto-assigned, send RIDE_ASSIGNED. Else RIDE_OFFER.
            async_to_sync(channel_layer.group_send)(
                f"driver_{driver.id}_rides",
                {
                    "type": "ride_assigned" if auto_assign else "ride_offer",
                    "data": {
                        "ride_id": ride.id,
                        "pickup": {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
                        "drop":   {"lat": float(ride.drop_lat),   "lng": float(ride.drop_lng)},
                        "pickup_address": ride.pickup_address or "",
                        "drop_address":   ride.drop_address or "",
                        "fare_estimate": float(ride.base_fare),
                        "timeout": 60,
                        "is_auto_assigned": auto_assign,
                        "rejection_count": stats.rejection_count_today,
                        "rejections_until_auto": max(0, 3 - stats.rejection_count_today),
                        "rider": {
                             "name":   ride.rider.get_full_name() or ride.rider.username,
                             "rating": float(getattr(getattr(ride.rider, 'rider_stats', None), 'avg_rating', 5.0))
                        }
                    },
                },
            )

            # 2. Notify RIDER
            async_to_sync(channel_layer.group_send)(
                f"ride_{ride.id}",
                {
                    "type": "ride_update",
                    "event": "RIDE_ASSIGNED" if auto_assign else "RIDE_OFFERED",
                    "data": {
                        "ride": {
                            "id": ride.id,
                            "status": ride.status,
                            "driver_id": driver.id,
                            "driver": {
                                "id": driver.id,
                                "name": driver.user.get_full_name() or driver.user.username,
                                "lat": float(driver.last_lat) if driver.last_lat else None,
                                "lng": float(driver.last_lng) if driver.last_lng else None,
                                "status": driver.status,
                            }
                        }
                    },
                },
            )

            # 3. Notify ADMIN
            async_to_sync(channel_layer.group_send)(
                "admin_live_map",
                {
                    "type": "admin_generic_event",
                    "event": "RIDE_STATUS_UPDATED",
                    "data": {
                        "ride_id": ride.id,
                        "status": ride.status,
                        "driver_id": driver.id,
                        "driver_name": driver.user.get_full_name() or driver.user.username,
                        "driver_status": driver.status,
                        "rider_id": ride.rider_id,
                        "nearby_driver_ids": candidate_ids,  # Highlight ALL considered drivers
                        "ride": {
                             "id": ride.id,
                             "status": ride.status,
                             "pickup":  {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
                             "dropoff": {"lat": float(ride.drop_lat),   "lng": float(ride.drop_lng)},
                             "pickup_address": ride.pickup_address or "",
                             "drop_address":   ride.drop_address or "",
                             "polyline":       ride.planned_route_polyline,
                             "rider_id":       ride.rider_id,
                             "rider_name":     ride.rider.get_full_name() or ride.rider.username,
                             "vehicle_type":   ride.vehicle_type,
                        }
                    },
                },
            )

            # 4. Push Notification
            Notification.objects.create(
                user=driver.user,
                channel="PUSH",
                type="AUTO_ASSIGNED" if auto_assign else "NEW_RIDE_OFFER",
                payload={
                    "ride_id": ride.id,
                    "title": "You have a new ride!" if auto_assign else "New Ride Request",
                    "body": f"Pick up at {ride.pickup_address}" if auto_assign else "Accept now to earn!",
                    "data": {"ride_id": str(ride.id)}
                }
            )

        transaction.on_commit(notify)
        logger.info(f"Ride {ride.id} {'ASSIGNED' if auto_assign else 'OFFERED'} to Driver {driver.id}")
