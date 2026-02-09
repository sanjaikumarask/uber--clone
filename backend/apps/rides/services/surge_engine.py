# apps/rides/services/surge_engine.py

from apps.common.redis import redis_client

SURGE_MIN = 1.0
SURGE_MAX = 3.0
SURGE_TTL = 60  # seconds


def cell_id_from_lat_lng(lat: float, lng: float) -> str:
    return f"{round(lat, 2)}:{round(lng, 2)}"


def _clamp(value: float) -> float:
    return max(SURGE_MIN, min(SURGE_MAX, value))


def recompute_surge(cell_id: str):
    """
    surge = demand / supply
    """
    demand = int(redis_client.get(f"geo:{cell_id}:demand") or 0)
    supply = int(redis_client.get(f"geo:{cell_id}:supply") or 0)

    if supply <= 0:
        surge = SURGE_MAX
    else:
        surge = demand / supply

    surge = _clamp(surge)

    redis_client.setex(
        f"geo:{cell_id}:surge",
        SURGE_TTL,
        surge,
    )

    return surge


# ----------------------------
# COUNTERS
# ----------------------------

def increment_demand(cell_id: str):
    redis_client.incr(f"geo:{cell_id}:demand")
    recompute_surge(cell_id)


def decrement_demand(cell_id: str):
    redis_client.decr(f"geo:{cell_id}:demand")
    recompute_surge(cell_id)


def increment_supply(cell_id: str):
    redis_client.incr(f"geo:{cell_id}:supply")
    recompute_surge(cell_id)


def decrement_supply(cell_id: str):
    redis_client.decr(f"geo:{cell_id}:supply")
    recompute_surge(cell_id)
