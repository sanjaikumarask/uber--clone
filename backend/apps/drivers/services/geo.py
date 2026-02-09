from apps.drivers.redis import redis_client

GEO_KEY = "drivers:geo"


def add_driver_to_geo(*, driver_id, lat, lng):
    redis_client.geoadd(GEO_KEY, (lng, lat, str(driver_id)))


def remove_driver_from_geo(*, driver_id):
    redis_client.zrem(GEO_KEY, str(driver_id))


def get_nearby_driver_ids(*, lat, lng, radius_km=5, limit=5):
    return [
        int(x)
        for x in redis_client.geosearch(
            GEO_KEY,
            longitude=lng,
            latitude=lat,
            radius=radius_km,
            unit="km",
            count=limit,
        )
    ]
