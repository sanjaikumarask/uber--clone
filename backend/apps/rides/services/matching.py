import logging
import time
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.notifications.models import Notification
from apps.drivers.services.geo import get_nearby_driver_ids
from apps.rides.services.lifecycle import update_ride_status
from apps.rides.tasks import driver_accept_timeout
from apps.common.metrics import RIDE_MATCH_ATTEMPTS, RIDE_MATCH_SUCCESS, RIDE_MATCH_LATENCY

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def find_driver_and_offer_ride(ride_id: int):
    """
    Matching Engine:
    Priority: 1) Level, 2) Score, 3) Distance (preserved via geo order).
    """
    start_time = time.time()
    
    with transaction.atomic():
        ride = Ride.objects.select_for_update().filter(id=ride_id).first()

        if not ride or ride.status != Ride.Status.SEARCHING:
            return

        RIDE_MATCH_ATTEMPTS.labels(city=ride.city, vehicle_type=ride.vehicle_type).inc()

        candidate_ids = get_nearby_driver_ids(
            lat=ride.pickup_lat,
            lng=ride.pickup_lng,
            radius_km=10.0,
            limit=20,
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
        
        from apps.drivers.services.geo import is_driver_locked, lock_driver_for_offer

        # logger.info(f"Checking {len(valid_candidate_ids)} candidates against ONLINE status in DB")
        online_driver_ids = set(
            Driver.objects.filter(
                id__in=valid_candidate_ids,
                status=Driver.Status.ONLINE
            ).values_list('id', flat=True)
        )

        # 🚨 FIX: Don't remove from GEO aggressively here. 
        # If they are in GEO but OFFLINE in DB, just skip them for this request.
        # remove_driver_from_geo(driver_id=cid) is handled by periodic pruning.

        db_candidates = (
            Driver.objects
            .select_for_update(of=("self",), skip_locked=True)
            .select_related("user", "stats")
            .filter(
                id__in=online_driver_ids,
                stats__trust_score__gte=60.0,
                stats__is_suspended=False,
            )
        )

        geo_order = {d_id: idx for idx, d_id in enumerate(valid_candidate_ids)}
        sorted_candidates = sorted(
            db_candidates,
            key=lambda d: (
                -LEVEL_PRIORITY.get(d.level, 1),
                -(getattr(d.stats, "score", 0.0) if hasattr(d, "stats") else 0.0),
                geo_order.get(d.id, 999),
            ),
        )

        available_candidates = []
        for d in sorted_candidates:
            if not is_driver_locked(driver_id=d.id):
                available_candidates.append(d)

        driver = available_candidates[0] if available_candidates else None

        if not driver:
            logger.info(f"Ride {ride.id}: No eligible drivers after sorting and lock checks.")
            return

        if not lock_driver_for_offer(driver_id=driver.id):
            return 

        from apps.drivers.models import DriverStats
        from apps.drivers.services.metrics import update_driver_metrics
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        stats.check_and_reset_daily_stats()

        auto_assign = stats.rejection_count_today >= 3

        update_driver_metrics(driver, "OFFERED")

        # ── ATTACH DRIVER & TRANSITION ──
        # We must attach the driver before calling the lifecycle service so it can
        # correctly generate OTPs and broadcast to the right groups.
        ride.driver = driver
        update_ride_status(ride, Ride.Status.ASSIGNED if auto_assign else Ride.Status.OFFERED)

        if not auto_assign:
             driver_accept_timeout.apply_async((ride.id, driver.id), countdown=60)
        else:
             update_driver_metrics(driver, "ACCEPTED")


        # Record success and latency
        RIDE_MATCH_SUCCESS.labels(city=ride.city, vehicle_type=ride.vehicle_type).inc()
        RIDE_MATCH_LATENCY.observe(time.time() - start_time)

        def notify():
            # 1. Notify DRIVER
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
                        "nearby_driver_ids": candidate_ids,  
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

            # 4. Stream event to KAFKA (Architecture Match)
            try:
                from apps.rides.kafka import publish_ride_match_event
                publish_ride_match_event(ride=ride, driver_ids=valid_candidate_ids)
            except Exception as e:
                logger.warning(f"Kafka stream error: {e}")


        transaction.on_commit(notify)
        logger.info(f"Ride {ride.id} {'ASSIGNED' if auto_assign else 'OFFERED'} to Driver {driver.id}")
