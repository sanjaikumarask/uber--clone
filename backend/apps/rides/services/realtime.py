# apps/rides/services/realtime.py
import logging

import polyline
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from apps.drivers.redis import redis_client

logger = logging.getLogger(__name__)

RIDE_DIST_KEY = "ride:{}:distance"
RIDE_PATH_KEY = "ride:{}:path"


def broadcast_ride_update(ride_id: int, *, event: str, data: dict):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"ride_{ride_id}",
        {
            "type": "ride_update",  # 🔥 MUST MATCH consumer method
            "event": event,  # e.g. DRIVER_LOCATION_UPDATED
            "data": data,
        },
    )


def buffer_ride_progress(ride_id: int, lat: float, lng: float, delta_km: float):
    """
    Buffers ride distance and GPS path in Redis to avoid Postgres write floods.
    Highly scalable: Handles 100k+ concurrent drivers by offloading IO to Redis.
    """
    pipe = redis_client.pipeline()

    # 1. Accumulate distance (using INCRBYFLOAT for atomic summation)
    if delta_km > 0:
        pipe.incrbyfloat(RIDE_DIST_KEY.format(ride_id), delta_km)

    # 2. Append coordinates to a list (for final polyline generation)
    pipe.rpush(RIDE_PATH_KEY.format(ride_id), f"{lat},{lng}")

    # 3. Set expiry (TTL) for 24h
    pipe.expire(RIDE_DIST_KEY.format(ride_id), 86400)
    pipe.expire(RIDE_PATH_KEY.format(ride_id), 86400)

    pipe.execute()


def get_buffered_ride_history(ride_id: int):
    """
    Retrieves the current ride distance and path from Redis.
    """
    dist = redis_client.get(RIDE_DIST_KEY.format(ride_id)) or 0
    path_raw = redis_client.lrange(RIDE_PATH_KEY.format(ride_id), 0, -1)

    path = []
    for p in path_raw:
        try:
            lat, lng = map(float, p.split(","))
            path.append((lat, lng))
        except ValueError:
            continue

    return {
        "distance_km": float(dist),
        "path": path,
        "polyline": polyline.encode(path) if path else "",
    }


@transaction.atomic
def persist_ride_history_to_db(ride_id: int):
    """
    Final synchronization from Redis to PostgreSQL at Trip Completion.
    """
    from apps.rides.models import Ride

    history = get_buffered_ride_history(ride_id)

    ride = Ride.objects.select_for_update().get(id=ride_id)
    ride.actual_distance_km = history["distance_km"]
    ride.actual_route_polyline = history["polyline"]
    ride.save(update_fields=["actual_distance_km", "actual_route_polyline"])

    # Cleanup Redis
    redis_client.delete(RIDE_DIST_KEY.format(ride_id))
    redis_client.delete(RIDE_PATH_KEY.format(ride_id))

    return ride
