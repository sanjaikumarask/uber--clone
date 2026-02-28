# apps/rides/services/surge.py

from apps.common.redis import redis_client
from .surge_engine import cell_id_from_lat_lng

SURGE_TTL = 60  # seconds


def get_surge_multiplier(cell_id: str) -> float:
    value = redis_client.get(f"geo:{cell_id}:surge")
    return float(value) if value else 1.0

def get_surge(lat: float, lng: float) -> float:
    cell_id = cell_id_from_lat_lng(lat, lng)
    return get_surge_multiplier(cell_id)
