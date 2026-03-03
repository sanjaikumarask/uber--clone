import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from celery import shared_task

from apps.rides.models import Ride
from apps.rides.services.cancellation import cancel_ride
from apps.rides.services.complete_ride import complete_ride

logger = logging.getLogger(__name__)

@shared_task
def auto_resolve_stale_rides():
    """
    SLA System: Auto-completes or cancels abandoned rides.
    Prevents riders and drivers from being 'locked' in dead sessions.
    """
    now = timezone.now()

    # 1. Cancel SEARCHING for > 15 mins
    searching_cutoff = now - timedelta(minutes=15)
    stale_searching = Ride.objects.filter(
        status=Ride.Status.SEARCHING, 
        created_at__lt=searching_cutoff
    )
    for ride in stale_searching:
        cancel_ride(ride, by=Ride.CancelledBy.SYSTEM)
        logger.warning(f"AUTO: Cancelled stale searching ride {ride.id}", extra={"ride_id": ride.id})

    # 2. Complete abandoned ONGOING/ARRIVED rides (> 12 hours)
    # This prevents ghost sessions if the app crashed mid-trip
    ongoing_cutoff = now - timedelta(hours=12)
    abandoned_rides = Ride.objects.filter(
        status__in=[Ride.Status.ONGOING, Ride.Status.ARRIVED],
        updated_at__lt=ongoing_cutoff
    )
    for ride in abandoned_rides:
        try:
            if ride.status == Ride.Status.ONGOING:
                complete_ride(ride.id)
                logger.warning(f"AUTO: Completed abandoned ongoing ride {ride.id}", extra={"ride_id": ride.id})
            else:
                cancel_ride(ride, by=Ride.CancelledBy.SYSTEM)
                logger.warning(f"AUTO: Cancelled abandoned arrived/assigned ride {ride.id}", extra={"ride_id": ride.id})
        except Exception as e:
            logger.error(f"AUTO: Failed to resolve abandoned ride {ride.id}: {e}", extra={"ride_id": ride.id})

    return f"Processed {stale_searching.count() + abandoned_rides.count()} stale/abandoned rides."
