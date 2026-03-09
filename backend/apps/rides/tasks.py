# apps/rides/tasks.py

from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.drivers.models import Driver
from apps.drivers.services.geo import add_driver_to_geo
from apps.drivers.services.metrics import update_driver_metrics
from apps.rides.models import Ride
from apps.rides.services.no_show import handle_no_show
from apps.rides.services.surge_engine import (
    cell_id_from_lat_lng,
    decrement_demand,
    increment_demand,
    increment_supply,
)

WAIT_TIME_MINUTES = 5


# ============================================================
# DRIVER ACCEPT TIMEOUT
# ============================================================
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def driver_accept_timeout(self, ride_id: int, driver_id: int):
    from apps.rides.services.matching import find_driver_and_offer_ride

    with transaction.atomic():
        ride = (
            Ride.objects.select_for_update()
            .filter(
                id=ride_id,
                driver_id=driver_id,
                status=Ride.Status.OFFERED,
            )
            .first()
        )

        if not ride:
            return

        driver = Driver.objects.select_for_update().get(id=driver_id)
        cell_id = cell_id_from_lat_lng(
            ride.pickup_lat,
            ride.pickup_lng,
        )

        ride.driver = None
        ride.transition_to(Ride.Status.SEARCHING)

        # Mark as rejected/timeout
        rejected = ride.rejected_driver_ids or []
        rejected.append(driver_id)
        ride.rejected_driver_ids = rejected

        # We must save rejected_driver_ids as well
        ride.save(
            update_fields=["driver", "status", "rejected_driver_ids", "updated_at"]
        )

        increment_demand(cell_id)
        increment_supply(cell_id)

        driver.status = Driver.Status.ONLINE
        driver.save(update_fields=["status"])

        if driver.last_lat and driver.last_lng:
            add_driver_to_geo(
                driver_id=driver.id,
                lat=driver.last_lat,
                lng=driver.last_lng,
            )

        transaction.on_commit(lambda: find_driver_and_offer_ride(ride.id))


# ============================================================
# NO-SHOW CHECK
# ============================================================
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def check_no_show(self, ride_id: int):
    with transaction.atomic():
        ride = Ride.objects.select_for_update().get(id=ride_id)

        if ride.status != Ride.Status.ARRIVED:
            return

        if not ride.arrived_at:
            return

        if timezone.now() < ride.arrived_at + timedelta(minutes=WAIT_TIME_MINUTES):
            return

        cell_id = cell_id_from_lat_lng(
            ride.pickup_lat,
            ride.pickup_lng,
        )

        handle_no_show(ride=ride)

        if ride.driver:
            update_driver_metrics(ride.driver, "NO_SHOW")

        decrement_demand(cell_id)
        increment_supply(cell_id)


@shared_task
def retry_matching_for_searching_rides():
    """
    Periodic task to pick up rides that are stuck in SEARCHING state.
    """
    from apps.rides.services.matching import find_driver_and_offer_ride

    searching_rides = Ride.objects.filter(status=Ride.Status.SEARCHING)
    for ride in searching_rides:
        find_driver_and_offer_ride(ride.id)


@shared_task
def auto_resolve_stuck_rides():
    """
    Handle failures:
    - Cancel rides SEARCHING for > 15 minutes.
    - Attempt to COMPLETE or CANCEL rides ONGOING for > 24 hours (App crash logic).
    """
    from apps.rides.services.cancellation import cancel_ride
    from apps.rides.services.complete_ride import complete_ride

    now = timezone.now()

    # 1. Cancel stale SEARCHING rides (> 15 mins since last update)
    stale_threshold = now - timedelta(minutes=15)
    stale_searching = Ride.objects.filter(
        status=Ride.Status.SEARCHING, updated_at__lt=stale_threshold
    )
    for ride in stale_searching:
        try:
            cancel_ride(ride=ride, by=Ride.CancelledBy.SYSTEM)
        except Exception:
            pass

    # 2. Complete abandoned ONGOING/ASSIGNED rides (> 24 hours)
    # This catches edge-cases where driver/rider force-close app without finishing
    abandoned_threshold = now - timedelta(hours=24)
    abandoned_active = Ride.objects.filter(
        status__in=[Ride.Status.ONGOING, Ride.Status.ARRIVED, Ride.Status.ASSIGNED],
        updated_at__lt=abandoned_threshold,
    )
    for ride in abandoned_active:
        try:
            if ride.status == Ride.Status.ONGOING:
                complete_ride(ride.id)
            else:
                cancel_ride(ride=ride, by=Ride.CancelledBy.SYSTEM)
        except Exception:
            pass
