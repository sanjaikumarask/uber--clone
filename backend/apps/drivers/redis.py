# apps/drivers/redis.py

import time
import redis
from django.conf import settings

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

DRIVER_TTL = 10  # seconds


def update_driver_location(driver_id: int, lat: float, lng: float):
    now = int(time.time())

    redis_client.geoadd(
        "drivers:live",
        lng,
        lat,
        f"driver:{driver_id}",
    )

    redis_client.hset(
        f"driver:{driver_id}:meta",
        mapping={
            "driver_id": driver_id,
            "last_seen": now,
        },
    )

    redis_client.setex(
        f"driver:{driver_id}:last_seen",
        DRIVER_TTL,
        now,
    )


# ----------------------------
# PHASE 4 ADDITIONS
# ----------------------------

def get_driver_last_point(driver_id):
    key = f"driver:{driver_id}:last_point"
    data = redis_client.hgetall(key)
    if not data:
        return None
    return float(data["lat"]), float(data["lng"])


def set_driver_last_point(driver_id, lat, lng):
    redis_client.hset(
        f"driver:{driver_id}:last_point",
        mapping={"lat": lat, "lng": lng},
    )


def clear_driver_last_point(driver_id):
    redis_client.delete(f"driver:{driver_id}:last_point")


def remove_driver_from_geo(driver_id: int):
    redis_client.zrem("drivers:live", f"driver:{driver_id}")
    redis_client.delete(f"driver:{driver_id}:meta")
    redis_client.delete(f"driver:{driver_id}:last_seen")
    clear_driver_last_point(driver_id)
