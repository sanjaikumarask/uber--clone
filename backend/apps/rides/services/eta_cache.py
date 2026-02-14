# apps/rides/services/eta_cache.py

from apps.common.redis import redis_client

ETA_TTL = 30  # seconds


def cache_planned_eta(ride_id: int, eta_min: float):
    redis_client.setex(
        f"ride:{ride_id}:eta",
        ETA_TTL,
        int(eta_min),
    )


def get_cached_eta(ride_id: int):
    raw = redis_client.get(f"ride:{ride_id}:eta")
    return int(raw) if raw else None

# Helper Alias
set_cached_eta = cache_planned_eta
