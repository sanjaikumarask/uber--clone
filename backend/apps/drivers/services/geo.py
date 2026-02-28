import logging
from apps.drivers.redis import redis_client, DRIVER_GEO_KEY

logger = logging.getLogger(__name__)

GEO_KEY = DRIVER_GEO_KEY


def add_driver_to_geo(*, driver_id, lat, lng):
    redis_client.geoadd(GEO_KEY, (lng, lat, str(driver_id)))


def remove_driver_from_geo(*, driver_id):
    redis_client.zrem(GEO_KEY, str(driver_id))


def get_nearby_driver_ids(*, lat, lng, radius_km=5, limit=5):
    logger.info(f"Checking nearby drivers at ({lat}, {lng}) radius={radius_km}km")
    
    # 1. Debug: Check total count in GEO_KEY
    total_count = redis_client.zcard(GEO_KEY)
    logger.info(f"Total drivers in Redis ({GEO_KEY}): {total_count}")

    # 2. Search
    results = redis_client.geosearch(
        GEO_KEY,
        longitude=lng,
        latitude=lat,
        radius=radius_km,
        unit="km",
        count=limit,
    )
    
    driver_ids = [int(x) for x in results]
    logger.info(f"Candidates from GEO search: {driver_ids}")

    # 3. Filter by Heartbeat (TTL)
    valid_ids = []
    for d_id in driver_ids:
        if redis_client.exists(f"driver:{d_id}:last_seen"):
            valid_ids.append(d_id)
        else:
            logger.info(f"Driver {d_id} heartbeat expired. Removing from GEO.")
            remove_driver_from_geo(driver_id=d_id)
    
    logger.info(f"Found valid nearby driver IDs (active heartbeats): {valid_ids}")
    return valid_ids
