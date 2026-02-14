import math

AVERAGE_SPEED_KMPH = 25.0  # conservative city avg


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0  # Earth radius in KM

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculate_eta_minutes(distance_km: float) -> int:
    hours = distance_km / AVERAGE_SPEED_KMPH
    return max(1, int(hours * 60))


def calculate_eta(lat1, lng1, lat2, lng2) -> int:
    """Helper used by eta_updater.py"""
    dist_km = haversine_km(lat1, lng1, lat2, lng2)
    return calculate_eta_minutes(dist_km)
