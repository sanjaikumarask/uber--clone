# apps/rides/services/fare.py
"""
Fare ESTIMATION service (called at booking time, before the ride starts).
Uses FareConfig from DB so estimates match actual final fare logic.
"""

import logging
from decimal import Decimal
from .distance import get_distance_and_duration
from apps.rides.fare_models import FareConfig
from .surge import get_surge

logger = logging.getLogger(__name__)


def estimate_fare(pickup: tuple, drop: tuple, vehicle_type: str = "go") -> dict:
    """
    pickup = (lat, lng)
    drop   = (lat, lng)

    Returns estimated fare using the same formula as final_fare.py
    so the estimate shown to riders is accurate.
    """
    config = FareConfig.get_for(vehicle_type)

    try:
        distance_km, duration_min = get_distance_and_duration(pickup, drop)
    except Exception as e:
        logger.warning(f"Distance API failed ({e}), using fallback 5km / 15min")
        distance_km  = 5.0
        duration_min = 15.0

    # ── Distance charge (same formula as final_fare) ─────────────────
    actual_km       = Decimal(str(distance_km))
    base_km         = config.base_distance_km
    extra_km        = max(Decimal("0"), actual_km - base_km)
    distance_charge = extra_km * config.per_km_rate

    # ── Duration component (for estimation only) ──────────────────────
    # Not used in final fare (final fare uses waiting time, not duration)
    duration_charge = Decimal(str(duration_min)) * config.per_min_rate

    # ── Surge multiplier ──────────────────────────────────────────────
    surge = get_surge(pickup[0], pickup[1])

    # ── Assemble ──────────────────────────────────────────────────────
    fare = (
        config.base_fare + distance_charge + duration_charge
    ) * Decimal(str(surge))

    if fare < config.minimum_fare:
        fare = config.minimum_fare

    return {
        "distance_km":      round(distance_km, 2),
        "duration_min":     round(duration_min, 1),
        "estimated_fare":   fare.quantize(Decimal("0.01")),
        "surge_multiplier": surge,
        # Fare breakdown for display:
        "base_fare":        str(config.base_fare),
        "per_km_rate":      str(config.per_km_rate),
    }
