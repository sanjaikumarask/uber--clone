# apps/rides/services/final_fare.py

from decimal import Decimal
from apps.rides import fare_config
from apps.rides.services.surge import get_surge_multiplier


def calculate_final_fare(
    *,
    base_fare: Decimal,
    actual_distance_km: float,
    surge_cell_id: str,
) -> Decimal:
    """
    Phase 4 FINAL RULE:
    - Fare is based ONLY on actual_distance_km
    - Called ONCE at ride completion
    - Deterministic & auditable
    """

    surge = Decimal(str(get_surge_multiplier(surge_cell_id)))

    fare = (
        base_fare +
        Decimal(actual_distance_km) * fare_config.PER_KM_RATE
    ) * surge

    if fare < fare_config.MINIMUM_FARE:
        fare = fare_config.MINIMUM_FARE

    return fare.quantize(Decimal("0.01"))
