# apps/rides/services/fare.py

from decimal import Decimal
from .distance import get_distance_and_duration
from apps.rides import fare_config


def estimate_fare(pickup, drop):
    """
    pickup = (lat, lng)
    drop = (lat, lng)
    """

    try:
        distance_km, duration_min = get_distance_and_duration(pickup, drop)
    except Exception:
        # 🚑 DEV FALLBACK (ABSOLUTELY REQUIRED)
        distance_km = 5.0
        duration_min = 15.0

    fare = (
        fare_config.BASE_FARE +
        Decimal(distance_km) * fare_config.PER_KM_RATE +
        Decimal(duration_min) * fare_config.PER_MIN_RATE
    ) * fare_config.SURGE_MULTIPLIER

    if fare < fare_config.MINIMUM_FARE:
        fare = fare_config.MINIMUM_FARE

    return {
        "distance_km": round(distance_km, 2),
        "duration_min": round(duration_min, 1),
        "estimated_fare": fare.quantize(Decimal("0.01")),
    }
