import math
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RoutePlanningError(Exception):
    pass

def haversine_km(lat1, lng1, lat2, lng2):
    """
    Approximate distance between two lat/lng points in KM (Fallback)
    """
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (math.sin(d_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_planned_route(origin, destination):
    """
    Calculates route using Google Directions API.
    origin: (lat, lng) tuple
    destination: (lat, lng) tuple
    """
    lat1, lng1 = origin
    lat2, lng2 = destination
    
    # -------------------------------
    # 1. TRY GOOGLE DIRECTIONS API
    # -------------------------------
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)

    if api_key:
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{lat1},{lng1}",
                "destination": f"{lat2},{lng2}",
                "mode": "driving",
                "key": api_key,
                # "departure_time": "now" # Optional: for traffic aware routing
            }

            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()

            if resp.status_code == 200 and data.get("status") == "OK":
                route = data["routes"][0]
                leg = route["legs"][0]
                
                logger.info("✅ Google Maps Route Calculated")
                return {
                    "polyline": route["overview_polyline"]["points"],
                    "distance_km": leg["distance"]["value"] / 1000,
                    "duration_min": leg["duration"]["value"] / 60,
                }
            else:
                logger.error(f"⚠️ Google Maps Error: {data.get('status')} - {data.get('error_message')}")

        except Exception as e:
            logger.error(f"⚠️ Google Maps Request Failed: {str(e)}")

    # -------------------------------
    # 2. FALLBACK (Haversine Math)
    # -------------------------------
    # If API key is missing or request fails, we estimate it so the app doesn't crash.
    logger.warning("Using Local Math Fallback for Route")
    dist = haversine_km(lat1, lng1, lat2, lng2)
    
    return {
        "polyline": "",  # No visual path in fallback mode
        "distance_km": round(dist, 2),
        "duration_min": round((dist / 30) * 60), # Assume 30km/h avg speed
    }

def get_distance_and_duration(origin, destination):
    """Helper wrapper for fare calculation which expects tuple"""
    res = get_planned_route(origin, destination)
    return res["distance_km"], res["duration_min"]