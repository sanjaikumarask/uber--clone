import math
import polyline
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def point_to_segment_distance(pt, s1, s2):
    """
    Minimum distance from point pt to line segment (s1, s2).
    pt, s1, s2 are (lat, lng) tuples.
    """
    px, py = pt
    x1, y1 = s1
    x2, y2 = s2
    
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return haversine_distance(px, py, x1, y1)
    
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    
    if t < 0:
        return haversine_distance(px, py, x1, y1)
    elif t > 1:
        return haversine_distance(px, py, x2, y2)
    
    closest_lat = x1 + t * dx
    closest_lng = y1 + t * dy
    return haversine_distance(px, py, closest_lat, closest_lng)

def check_route_deviation(driver, ride, current_lat, current_lng, threshold_m=None):
    """
    Checks if the driver has strayed too far from the planned polyline.
    If deviated, sends a WebSocket alert to the admin group.
    """
    if threshold_m is None:
        from apps.tracking.geo import DEVIATION_THRESHOLD_METERS
        threshold_m = DEVIATION_THRESHOLD_METERS

    if not ride.planned_route_polyline:
        return False, 0

    try:
        points = polyline.decode(ride.planned_route_polyline)
        if not points:
            return False, 0
        
        # Find minimum distance to any segment of the polyline
        min_dist = float('inf')
        for i in range(len(points) - 1):
            dist = point_to_segment_distance((current_lat, current_lng), points[i], points[i+1])
            if dist < min_dist:
                min_dist = dist
        
        is_deviated = min_dist > threshold_m
        
        if is_deviated:
            # 🚨 Rate limit alerts to once every 30 seconds per ride using Redis
            from django.core.cache import cache
            lock_key = f"deviation_alert_lock_{ride.id}"
            if not cache.get(lock_key):
                cache.set(lock_key, True, 30)
                
                # Broadcast alert to Admin Dashboard
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_live_map",
                    {
                        "type": "route_deviation_alert",
                        "data": {
                            "driver_id": driver.id,
                            "driver_name": f"{driver.user.first_name} {driver.user.last_name}",
                            "ride_id": ride.id,
                            "deviation_m": round(min_dist),
                            "lat": current_lat,
                            "lng": current_lng,
                        }
                    }
                )
            
        return is_deviated, min_dist
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error checking route deviation: {e}")
        return False, 0
