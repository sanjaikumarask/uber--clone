# apps/rides/services/distance.py

import math
import requests
from django.conf import settings


class RoutePlanningError(Exception):
    pass


def haversine_km(lat1, lng1, lat2, lng2):
    """
    Approximate distance between two lat/lng points in KM
    """
    R = 6371  # Earth radius in km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_planned_route(*, origin, destination):
    """
    Uses Google Directions API if available.
    Falls back to local approximation if billing/API fails.
    """

    lat1, lng1 = origin
    lat2, lng2 = destination

    # -------------------------------
    # TRY GOOGLE DIRECTIONS FIRST
    # -------------------------------
    if settings.GOOGLE_MAPS_API_KEY:
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{lat1},{lng1}",
                "destination": f"{lat2},{lng2}",
                "mode": "driving",
                "key": settings.GOOGLE_MAPS_API_KEY,
            }

            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()

            if resp.status_code == 200 and data.get("status") == "OK":
                route = data["routes"][0]
                leg = route["legs"][0]

                return {
                    "polyline": route["overview_polyline"]["points"],
                    "distance_km": leg["distance"]["value"] / 1000,
                    "duration_min": leg["duration"]["value"] / 60,
                }

        except Exception:
            pass  # fall back safely

    # -------------------------------
    # 🔥 FALLBACK (LOCAL MODE)
    # -------------------------------
    distance_km = haversine_km(lat1, lng1, lat2, lng2)

    return {
        "polyline": None,
        "distance_km": round(distance_km, 2),
        "duration_min": round((distance_km / 40) * 60, 1),  # avg 40km/h
    }
