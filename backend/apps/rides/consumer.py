import logging
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.drivers.services import remove_driver_from_geo
from apps.rides.tasks import driver_accept_timeout

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def handle_ride_searching(event: dict):
    if event.get("event") != "RIDE_SEARCHING":
        return

    ride_id = event.get("ride_id")
    driver_ids = event.get("driver_ids")

    if not ride_id or not driver_ids:
        return

    with transaction.atomic():
        ride = Ride.objects.select_for_update().get(id=ride_id)

        if ride.status != Ride.Status.SEARCHING:
            return

        for driver_id in driver_ids:
            driver = Driver.objects.filter(
                id=driver_id,
                status=Driver.Status.ONLINE,
            ).first()

            if not driver:
                continue

            driver = Driver.objects.select_for_update().get(id=driver.id)

            # ASSIGN
            ride.driver = driver
            ride.transition_to(Ride.Status.ASSIGNED)

            driver.transition_to(Driver.Status.BUSY)
            remove_driver_from_geo(driver_id=driver.id)

            # PUSH OFFER
            async_to_sync(channel_layer.group_send)(
                f"driver_{driver.user_id}",
                {
                    "type": "ride_request",
                    "data": {
                        "ride_id": ride.id,
                        "pickup": {
                            "lat": ride.pickup_lat,
                            "lng": ride.pickup_lng,
                        },
                        "drop": {
                            "lat": ride.drop_lat,
                            "lng": ride.drop_lng,
                        },
                        "fare_estimate": float(
                            ride.base_fare + ride.distance_fare
                        ),
                        "timeout": 30,
                    },
                },
            )

            transaction.on_commit(
                lambda r=ride.id, d=driver.id: driver_accept_timeout.apply_async(
                    args=[r, d],
                    countdown=30,
                )
            )

            logger.info(f"Ride {ride.id} offered to driver {driver.id}")
            return
