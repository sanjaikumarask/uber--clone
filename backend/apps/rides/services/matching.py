import logging
from django.db import transaction
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.drivers.services.geo import get_nearby_driver_ids

# If you don't have this notification service yet, you can comment this import out
# from apps.notifications.services.dispatcher import notify_driver_new_offer 

logger = logging.getLogger(__name__)

def find_driver_and_offer_ride(ride_id: int):
    """
    1. Finds nearby drivers.
    2. Filters out drivers who already rejected this ride.
    3. Picks the best candidate.
    4. Sets status to OFFERED (Broadcast step).
    """
    with transaction.atomic():
        # Lock the ride row
        ride = Ride.objects.select_for_update().filter(id=ride_id).first()
        
        if not ride:
            return
        
        # Only match if currently searching
        if ride.status != Ride.Status.SEARCHING:
            return

        # 1. Get Nearby Drivers (e.g., 5km radius)
        # We fetch more than 1 because we might need to skip rejected ones
        candidate_ids = get_nearby_driver_ids(
            lat=ride.pickup_lat,
            lng=ride.pickup_lng,
            radius_km=5.0,
            limit=10 
        )

        # 2. Filter out drivers who already rejected
        rejected_ids = set(ride.rejected_driver_ids or [])
        valid_candidates = [d_id for d_id in candidate_ids if d_id not in rejected_ids]

        if not valid_candidates:
            logger.info(f"Ride {ride.id}: No valid drivers found nearby.")
            # Optional: Expand radius logic here
            return

        # 3. Pick the first best candidate
        chosen_driver_id = valid_candidates[0]
        
        driver = Driver.objects.select_for_update().filter(
            id=chosen_driver_id, 
            status=Driver.Status.ONLINE
        ).first()

        if not driver:
            # Driver went offline or doesn't exist
            logger.warning(f"Driver {chosen_driver_id} not available/online.")
            return

        # 4. Set State to OFFERED (The "Broadcast" step in flowchart)
        ride.driver = driver
        ride.status = Ride.Status.OFFERED
        ride.save(update_fields=["driver", "status", "updated_at"])

        # 5. Notify the Driver (Socket/Push)
        # notify_driver_new_offer(driver.id, ride.id) 
        logger.info(f"Ride {ride.id} OFFERED to Driver {driver.id}")