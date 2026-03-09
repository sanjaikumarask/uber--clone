import logging

from django.conf import settings

from apps.drivers.redis import (
    redis_client,
)
from apps.rides.models import Ride
from apps.tracking.geo import (
    snap_to_roads,
)

logger = logging.getLogger(__name__)


class LocationProcessor:
    """Service to handle the business logic of a driver GPS ping."""

    @staticmethod
    def filter_noisy_ping(accuracy_m):
        return accuracy_m is not None and float(accuracy_m) > 120

    @staticmethod
    async def get_snapped_coords(lat, lng, seq):
        snap_error_key = "google_roads_403_circuit_breaker"
        if (seq % 10 == 0) and not redis_client.get(snap_error_key):
            try:
                snapped = await snap_to_roads(
                    lat, lng, api_key=settings.GOOGLE_MAPS_API_KEY
                )
                if snapped:
                    return snapped
            except Exception as e:
                logger.error(f"[LocationProcessor] SnapToRoads failed: {e}")
        return lat, lng

    @staticmethod
    def detect_fraud(ride, delta_km, elapsed_seconds):
        if elapsed_seconds > 0 and delta_km > 0:
            speed_kmh_calc = (delta_km / elapsed_seconds) * 3600
            if speed_kmh_calc > 150:
                logger.warning(
                    f"[LocationProcessor] 🚨 Velocity Violation: Ride {ride.id} speed {speed_kmh_calc:.1f} km/h"
                )
                ride.is_fraud_flagged = True
                ride.save(update_fields=["is_fraud_flagged"])
                return speed_kmh_calc > 500  # Return true if "teleportation"
        return False

    @staticmethod
    def calculate_eta(ride, lat, lng):
        from apps.tracking.geo import haversine_m

        if not ride:
            return None

        dest_lat, dest_lng = (
            (ride.pickup_lat, ride.pickup_lng)
            if ride.status in [Ride.Status.ASSIGNED, Ride.Status.ARRIVED]
            else (ride.drop_lat, ride.drop_lng)
        )
        dist_m = haversine_m(lat, lng, dest_lat, dest_lng)
        return int(max(1, (dist_m / 1000.0) / 0.41))
