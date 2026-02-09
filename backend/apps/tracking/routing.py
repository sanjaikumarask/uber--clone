# apps/tracking/routing.py

import math
import polyline

DEVIATION_THRESHOLD_METERS = 50


def decode_route(polyline_str):
    return polyline.decode(polyline_str)


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def snap_to_route(lat, lng, route_points):
    closest = None
    min_dist = float("inf")

    for rlat, rlng in route_points:
        d = haversine_m(lat, lng, rlat, rlng)
        if d < min_dist:
            min_dist = d
            closest = (rlat, rlng)

    return closest, min_dist


def is_deviated(distance_m):
    return distance_m > DEVIATION_THRESHOLD_METERS


# ----------------------------
# PHASE 4 ADDITION
# ----------------------------

def accumulate_distance(prev, curr):
    if not prev or not curr:
        return 0.0
    return haversine_m(
        prev[0], prev[1],
        curr[0], curr[1]
    ) / 1000.0
