import math
import polyline

DEVIATION_THRESHOLD_METERS = 300


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


def p_to_segment_dist(p_lat, p_lng, a_lat, a_lng, b_lat, b_lng):
    """
    Returns the minimum distance from point P to line segment AB.
    Uses projection. For simplicity at small scales, we treat as Cartesian.
    """
    # Convert to roughly consistent meters for vector math
    # 1 deg lat is ~111km, 1 deg lng at 13 deg N is ~108km
    px, py = p_lng * 108000, p_lat * 111000
    ax, ay = a_lng * 108000, a_lat * 111000
    bx, by = b_lng * 108000, b_lat * 111000

    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return haversine_m(p_lat, p_lng, a_lat, a_lng)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    
    snap_lat = a_lat + t * (b_lat - a_lat)
    snap_lng = a_lng + t * (b_lng - a_lng)
    
    return haversine_m(p_lat, p_lng, snap_lat, snap_lng), (snap_lat, snap_lng)


def snap_to_route(lat, lng, route_points):
    """
    Finds the closest point on the polyline (checking segments) to the given coordinate.
    """
    if not route_points:
        return (lat, lng), 0.0

    min_dist = float("inf")
    closest_point = (lat, lng)

    for i in range(len(route_points) - 1):
        a = route_points[i]
        b = route_points[i+1]
        dist, snapped = p_to_segment_dist(lat, lng, a[0], a[1], b[0], b[1])
        
        if dist < min_dist:
            min_dist = dist
            closest_point = snapped

    return closest_point, min_dist


def is_deviated(distance_m):
    return distance_m > DEVIATION_THRESHOLD_METERS


def accumulate_distance(prev, curr):
    if not prev or not curr:
        return 0.0

    return haversine_m(
        prev[0], prev[1],
        curr[0], curr[1],
    ) / 1000.0


def snap_to_roads(lat, lng, api_key=None):
    """
    Calls Google Roads API to snap a point to the nearest road.
    Fallbacks to input if fails.
    """
    if not api_key:
        return (lat, lng)

    try:
        import requests
        url = "https://roads.googleapis.com/v1/snapToRoads"
        params = {
            "path": f"{lat},{lng}",
            "interpolate": "false",
            "key": api_key
        }
        resp = requests.get(url, params=params, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            snapped_points = data.get("snappedPoints", [])
            if snapped_points:
                loc = snapped_points[0].get("location", {})
                return (loc.get("latitude", lat), loc.get("longitude", lng))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"snap_to_roads error: {e}")

    return (lat, lng)
