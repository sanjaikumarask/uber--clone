# apps/rides/services/surge.py

from apps.common.redis import redis_client

SURGE_TTL = 60  # seconds



def get_surge_multiplier(cell_id: str) -> float:
    value = redis_client.get(f"geo:{cell_id}:surge")
    return float(value) if value else 1.0

