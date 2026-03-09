import logging
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from apps.common.metrics import (
    RIDE_MATCH_ATTEMPTS,
    RIDE_MATCH_LATENCY,
    RIDE_MATCH_SUCCESS,
)
from apps.drivers.models import Driver
from apps.drivers.services.geo import get_nearby_driver_ids
from apps.notifications.models import Notification
from apps.rides.models import Ride
from apps.rides.services.lifecycle import update_ride_status
from apps.rides.tasks import driver_accept_timeout

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def _get_sorted_candidates(ride, rejected_ids):
    """Fetch nearby drivers and sort by Level, Score, and Proximity."""
    LEVEL_PRIORITY = {
        Driver.Level.PRO: 4,
        Driver.Level.CONSISTENT: 3,
        Driver.Level.ACTIVE: 2,
        Driver.Level.NORMAL: 1,
    }

    candidate_ids = get_nearby_driver_ids(
        lat=ride.pickup_lat,
        lng=ride.pickup_lng,
        radius_km=10.0,
        limit=20,
    )

    valid_ids = [cid for cid in candidate_ids if cid not in rejected_ids]
    if not valid_ids:
        return [], []

    online_driver_ids = set(
        Driver.objects.filter(
            id__in=valid_ids, status=Driver.Status.ONLINE
        ).values_list("id", flat=True)
    )

    db_candidates = (
        Driver.objects.select_for_update(of=("self",), skip_locked=True)
        .select_related("user", "stats")
        .filter(
            id__in=online_driver_ids,
            stats__trust_score__gte=60.0,
            stats__is_suspended=False,
        )
    )

    geo_order = {d_id: idx for idx, d_id in enumerate(valid_ids)}

    def sorting_key(d):
        return (
            -LEVEL_PRIORITY.get(d.level, 1),
            -(getattr(d.stats, "score", 0.0) if hasattr(d, "stats") else 0.0),
            geo_order.get(d.id, 999),
        )

    return sorted(db_candidates, key=sorting_key), candidate_ids


def _notify_match_event(
    ride, driver, auto_assign, candidate_ids, valid_candidate_ids, stats
):
    """Handles multi-channel notifications on successful ride matching."""

    # 1. Notify DRIVER
    _notify_driver_of_match(ride, driver, auto_assign, stats)

    # 2. Notify RIDER
    _notify_rider_of_match(ride, driver, auto_assign)

    # 3. Notify ADMIN
    _notify_admin_of_match(ride, driver, candidate_ids)

    # 4. Push Notification
    _send_match_push_notification(ride, driver, auto_assign)

    # 5. Kafka Stream
    _publish_kafka_match_event(ride, valid_candidate_ids)


def _notify_driver_of_match(ride, driver, auto_assign, stats):
    async_to_sync(channel_layer.group_send)(
        f"driver_{driver.id}_rides",
        {
            "type": "ride_assigned" if auto_assign else "ride_offer",
            "data": {
                "ride_id": ride.id,
                "pickup": {
                    "lat": float(ride.pickup_lat),
                    "lng": float(ride.pickup_lng),
                },
                "drop": {"lat": float(ride.drop_lat), "lng": float(ride.drop_lng)},
                "pickup_address": ride.pickup_address or "",
                "drop_address": ride.drop_address or "",
                "fare_estimate": float(ride.base_fare),
                "timeout": 60,
                "is_auto_assigned": auto_assign,
                "rejection_count": stats.rejection_count_today,
                "rejections_until_auto": max(0, 3 - stats.rejection_count_today),
                "rider": {
                    "name": ride.rider.get_full_name() or ride.rider.username,
                    "rating": float(
                        getattr(
                            getattr(ride.rider, "rider_stats", None), "avg_rating", 5.0
                        )
                    ),
                },
            },
        },
    )


def _notify_rider_of_match(ride, driver, auto_assign):
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
                    },
                }
            },
        },
    )


def _notify_admin_of_match(ride, driver, candidate_ids):
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
                    "pickup": {
                        "lat": float(ride.pickup_lat),
                        "lng": float(ride.pickup_lng),
                    },
                    "dropoff": {
                        "lat": float(ride.drop_lat),
                        "lng": float(ride.drop_lng),
                    },
                    "pickup_address": ride.pickup_address or "",
                    "drop_address": ride.drop_address or "",
                    "polyline": ride.planned_route_polyline,
                    "rider_id": ride.rider_id,
                    "rider_name": ride.rider.get_full_name() or ride.rider.username,
                    "vehicle_type": ride.vehicle_type,
                },
            },
        },
    )


def _send_match_push_notification(ride, driver, auto_assign):
    Notification.objects.create(
        user=driver.user,
        channel="PUSH",
        type="AUTO_ASSIGNED" if auto_assign else "NEW_RIDE_OFFER",
        payload={
            "ride_id": ride.id,
            "title": "You have a new ride!" if auto_assign else "New Ride Request",
            "body": (
                f"Pick up at {ride.pickup_address}"
                if auto_assign
                else "Accept now to earn!"
            ),
            "data": {"ride_id": str(ride.id)},
        },
    )


def _publish_kafka_match_event(ride, valid_candidate_ids):
    try:
        from apps.rides.kafka import publish_ride_match_event

        publish_ride_match_event(ride=ride, driver_ids=valid_candidate_ids)
    except Exception as e:
        logger.warning(f"Kafka stream error: {e}")


def find_driver_and_offer_ride(ride_id: int):
    """
    Matching Engine Entry Point.
    Refactored to minimize cognitive complexity.
    """
    start_time = time.time()
    from apps.drivers.models import DriverStats
    from apps.drivers.services.geo import is_driver_locked, lock_driver_for_offer
    from apps.drivers.services.metrics import update_driver_metrics

    with transaction.atomic():
        ride = Ride.objects.select_for_update().filter(id=ride_id).first()
        if not ride or ride.status != Ride.Status.SEARCHING:
            return

        RIDE_MATCH_ATTEMPTS.labels(city=ride.city, vehicle_type=ride.vehicle_type).inc()

        rejected_ids = set(ride.rejected_driver_ids or [])
        sorted_candidates, candidate_ids = _get_sorted_candidates(ride, rejected_ids)

        driver = next(
            (d for d in sorted_candidates if not is_driver_locked(driver_id=d.id)), None
        )

        if not driver or not lock_driver_for_offer(driver_id=driver.id):
            logger.info(f"Ride {ride.id}: No eligible or available drivers.")
            return

        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        stats.check_and_reset_daily_stats()

        auto_assign = stats.rejection_count_today >= 3
        update_driver_metrics(driver, "OFFERED")

        # 1. Update status AND driver atomically via Lifecycle (Authority)
        new_status = Ride.Status.ASSIGNED if auto_assign else Ride.Status.OFFERED
        update_ride_status(ride, new_status, driver=driver)

        if not auto_assign:
            driver_accept_timeout.apply_async((ride.id, driver.id), countdown=60)
        else:
            update_driver_metrics(driver, "ACCEPTED")

        RIDE_MATCH_SUCCESS.labels(city=ride.city, vehicle_type=ride.vehicle_type).inc()
        RIDE_MATCH_LATENCY.observe(time.time() - start_time)

        valid_ids = [d.id for d in sorted_candidates]
        transaction.on_commit(
            lambda: _notify_match_event(
                ride, driver, auto_assign, candidate_ids, valid_ids, stats
            )
        )

    logger.info(
        f"Ride {ride.id} {'ASSIGNED' if auto_assign else 'OFFERED'} to Driver {driver.id}"
    )
