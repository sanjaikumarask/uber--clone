from django.db import transaction
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.drivers.services.geo import get_nearby_driver_ids
from apps.rides.services.otp import generate_and_attach_otp


def match_and_assign(ride_id: int):
    with transaction.atomic():
        ride = Ride.objects.select_for_update().get(
            id=ride_id,
            status=Ride.Status.SEARCHING,
        )

        driver_ids = get_nearby_driver_ids(
            lat=ride.pickup_lat,
            lng=ride.pickup_lng,
        )

        driver = (
            Driver.objects
            .select_for_update()
            .filter(id__in=driver_ids, status=Driver.Status.ONLINE)
            .first()
        )

        if not driver:
            return None

        ride.driver = driver
        ride.status = Ride.Status.ASSIGNED
        ride.save(update_fields=["driver", "status"])

        driver.status = Driver.Status.BUSY
        driver.save(update_fields=["status"])

        return driver.id
