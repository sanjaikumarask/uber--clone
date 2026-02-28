# apps/drivers/redis.py

import time
import redis
from django.conf import settings

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

DRIVER_TTL = 60  # seconds — must be > mobile GPS ping interval (typically 10-15s)
DRIVER_GEO_KEY = "drivers:geo"


# ───────────────────────────────────────────────
# LIVE LOCATION UPDATE (VERSION-SAFE)
# ───────────────────────────────────────────────
def update_driver_location(driver_id: int, lat: float, lng: float):
    """
    Update driver location in Redis using raw GEOADD command.
    This avoids redis-py version signature issues.
    """
    now = int(time.time())

    # Use raw Redis command to avoid geoadd() API mismatch
    redis_client.execute_command(
        "GEOADD",
        DRIVER_GEO_KEY,
        float(lng),
        float(lat),
        str(driver_id),
    )

    # Update metadata
    redis_client.hset(
        f"driver:{driver_id}:meta",
        mapping={
            "driver_id": driver_id,
            "last_seen": now,
        },
    )

    # TTL heartbeat key
    redis_client.setex(
        f"driver:{driver_id}:last_seen",
        DRIVER_TTL,
        now,
    )


# ───────────────────────────────────────────────
# DISTANCE ACCUMULATION SUPPORT
# ───────────────────────────────────────────────
def get_driver_last_point(driver_id):
    key = f"driver:{driver_id}:last_point"
    data = redis_client.hgetall(key)
    if not data:
        return None

    return float(data["lat"]), float(data["lng"])


def set_driver_last_point(driver_id, lat, lng):
    redis_client.hset(
        f"driver:{driver_id}:last_point",
        mapping={
            "lat": float(lat),
            "lng": float(lng),
        },
    )


def clear_driver_last_point(driver_id):
    redis_client.delete(f"driver:{driver_id}:last_point")


# ───────────────────────────────────────────────
# CLEANUP WHEN DRIVER GOES OFFLINE
# ───────────────────────────────────────────────
def remove_driver_from_geo(driver_id: int):
    redis_client.execute_command(
        "ZREM",
        DRIVER_GEO_KEY,
        str(driver_id),
    )

    redis_client.delete(f"driver:{driver_id}:meta")
    redis_client.delete(f"driver:{driver_id}:last_seen")
    clear_driver_last_point(driver_id)
