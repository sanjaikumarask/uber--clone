# apps/rides/tasks.py

from celery import shared_task
from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.drivers.services.geo import add_driver_to_geo
from apps.rides.kafka import publish_ride_searching_event
from apps.rides.services.no_show import handle_no_show
from apps.rides.services.surge_engine import (
    cell_id_from_lat_lng,
    increment_demand,
    decrement_demand,
    increment_supply,
)
from apps.drivers.services.trust import register_no_show

WAIT_TIME_MINUTES = 5


# ============================================================
# DRIVER ACCEPT TIMEOUT
# ============================================================
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def driver_accept_timeout(self, ride_id: int, driver_id: int):
    with transaction.atomic():
        ride = Ride.objects.select_for_update().filter(
            id=ride_id,
            driver_id=driver_id,
            status=Ride.Status.ASSIGNED,
        ).first()

        if not ride:
            return

        driver = Driver.objects.select_for_update().get(id=driver_id)
        cell_id = cell_id_from_lat_lng(
            ride.pickup_lat,
            ride.pickup_lng,
        )

        # rollback assignment
        ride.driver = None
        ride.transition_to(Ride.Status.SEARCHING)

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

        transaction.on_commit(
            lambda r=ride: publish_ride_searching_event(
                ride=r,
                driver_ids=[],
            )
        )


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
            register_no_show(ride.driver)

        decrement_demand(cell_id)
        increment_supply(cell_id)
