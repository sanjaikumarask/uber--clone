# apps/drivers/redis_rider.py

import time

import redis
from django.conf import settings

# Initialize Redis client separately for rider functions if needed,
# or reuse existing connection handling pattern
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

RIDER_TTL = 300  # 5 minutes (riders might be static longer)
RIDER_GEO_KEY = "riders:geo"


# ───────────────────────────────────────────────
# LIVE RIDER LOCATION UPDATE
# ───────────────────────────────────────────────
def update_rider_location(rider_id: int, lat: float, lng: float):
    """
    Update rider location in Redis using raw GEOADD command.
    """
    now = int(time.time())

    # Use raw Redis command to avoid geoadd() API mismatch
    redis_client.execute_command(
        "GEOADD",
        RIDER_GEO_KEY,
        float(lng),
        float(lat),
        str(rider_id),
    )

    # Update metadata
    redis_client.hset(
        f"rider:{rider_id}:meta",
        mapping={
            "rider_id": rider_id,
            "last_seen": now,
        },
    )

    # Set TTL on meta
    redis_client.expire(f"rider:{rider_id}:meta", RIDER_TTL)


# ───────────────────────────────────────────────
# RIDER LAST KNOWN LOCATION (FOR DRIVER ETA ETC)
# ───────────────────────────────────────────────
def get_rider_last_point(rider_id):
    key = f"rider:{rider_id}:last_point"
    data = redis_client.hgetall(key)
    if not data:
        return None

    return float(data["lat"]), float(data["lng"])


def set_rider_last_point(rider_id, lat, lng):
    redis_client.hset(
        f"rider:{rider_id}:last_point",
        mapping={
            "lat": float(lat),
            "lng": float(lng),
        },
    )
    # 1 hour expiry for last point, useful for history
    redis_client.expire(f"rider:{rider_id}:last_point", 3600)


def clear_rider_last_point(rider_id):
    redis_client.delete(f"rider:{rider_id}:last_point")


# ───────────────────────────────────────────────
# CLEANUP
# ───────────────────────────────────────────────
def remove_rider_from_geo(rider_id: int):
    redis_client.execute_command(
        "ZREM",
        RIDER_GEO_KEY,
        str(rider_id),
    )

    redis_client.delete(f"rider:{rider_id}:meta")
    clear_rider_last_point(rider_id)
