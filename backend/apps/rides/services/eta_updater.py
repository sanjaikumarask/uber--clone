import time
from apps.rides.services.eta import calculate_eta
from apps.rides.services.eta_cache import get_cached_eta, set_cached_eta

MIN_UPDATE_INTERVAL = 10  # seconds


def update_eta_if_needed(*, ride, driver_lat, driver_lng):
    cached = get_cached_eta(ride.id)

    if cached is not None:
        return cached

    eta = calculate_eta(
        driver_lat,
        driver_lng,
        ride.drop_lat,
        ride.drop_lng,
    )

    set_cached_eta(ride.id, eta)
    return eta
