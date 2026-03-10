# apps/rides/services/waiting_detector.py
"""
GPS-based waiting time detector for drivers.

Logic:
  - Speed < 2 km/h for >= 60 consecutive seconds → "waiting"
  - Speed >= 2 km/h → end waiting period
  - Debounce: state only changes if threshold is sustained (prevents GPS jitter)
  - Per-ride state stored in Redis for real-time tracking

Redis schema (per ride):
  ride:{id}:wait_state  → dict with keys:
    "is_waiting"        : bool
    "waiting_since"     : ISO timestamp or None
    "accumulated_secs"  : int (total confirmed waiting seconds so far)
    "low_speed_since"   : ISO timestamp or None (debounce start)
"""

import logging
import math
from datetime import datetime

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
WAITING_SPEED_THRESHOLD_KMH = 2.0  # Below this = potential waiting
WAITING_DEBOUNCE_SECONDS = 60  # Must be slow for this long before counting
CACHE_TTL = 3600  # 1 hour (clears after ride is done)


def _cache_key(ride_id: int) -> str:
    return f"ride:{ride_id}:wait_state"


def _get_state(ride_id: int) -> dict:
    raw = cache.get(_cache_key(ride_id))
    if raw:
        return raw
    return {
        "is_waiting": False,
        "waiting_since": None,
        "accumulated_secs": 0,
        "low_speed_since": None,
    }


def _set_state(ride_id: int, state: dict):
    cache.set(_cache_key(ride_id), state, CACHE_TTL)


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    """Distance between two GPS points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def compute_speed_kmh(
    lat1: float, lng1: float, lat2: float, lng2: float, elapsed_seconds: float
) -> float:
    """Compute speed between two GPS pings."""
    if elapsed_seconds <= 0:
        return 0.0
    distance_km = _haversine_km(lat1, lng1, lat2, lng2)
    return (distance_km / elapsed_seconds) * 3600


def process_location_update(
    ride_id: int,
    lat: float,
    lng: float,
    prev_lat: float,
    prev_lng: float,
    elapsed_seconds: float,
) -> dict:
    """
    Called every time the driver sends a GPS update during an ONGOING ride.

    Returns a dict with:
        - is_waiting (bool)
        - accumulated_secs (int): total waiting seconds accumulated so far
        - speed_kmh (float)
        - event (str): "waiting_started" | "waiting_ended" | "none"
    """
    if elapsed_seconds <= 0 or elapsed_seconds > 300:
        # Ignore stale/reconnected updates (> 5 min gap)
        return {
            "is_waiting": False,
            "accumulated_secs": 0,
            "speed_kmh": 0,
            "event": "none",
        }

    speed = compute_speed_kmh(lat, lng, prev_lat, prev_lng, elapsed_seconds)
    now = timezone.now()
    state = _get_state(ride_id)

    if speed < WAITING_SPEED_THRESHOLD_KMH:
        event = _handle_slow_ping(ride_id, speed, now, state)
    else:
        event = _handle_moving_ping(ride_id, speed, now, state)

    _set_state(ride_id, state)

    return {
        "is_waiting": state["is_waiting"],
        "accumulated_secs": state["accumulated_secs"],
        "speed_kmh": round(speed, 2),
        "event": event,
    }


def get_total_waiting_seconds(ride_id: int) -> int:
    """
    Returns total confirmed waiting seconds for the ride.
    Called at ride completion to lock the final value.
    """
    state = _get_state(ride_id)
    total = state["accumulated_secs"]

    # If currently waiting, add in-progress time
    if state["is_waiting"] and state["waiting_since"]:
        now = timezone.now()
        wait_start = datetime.fromisoformat(state["waiting_since"])
        total += int((now - wait_start).total_seconds())

    return max(0, total)


def clear_waiting_state(ride_id: int):
    """Call after ride is completed to clean up Redis."""
    cache.delete(_cache_key(ride_id))


def _handle_slow_ping(ride_id, speed, now, state):
    event = "none"
    if not state["low_speed_since"]:
        state["low_speed_since"] = now.isoformat()
    else:
        low_since = datetime.fromisoformat(state["low_speed_since"])
        if (now - low_since).total_seconds() >= WAITING_DEBOUNCE_SECONDS:
            if not state["is_waiting"]:
                state["is_waiting"] = True
                state["waiting_since"] = low_since.isoformat()
                event = "waiting_started"
                logger.info(f"Ride {ride_id}: WAITING STARTED. Speed={speed:.2f}km/h")
            elif state["waiting_since"]:
                wait_start = datetime.fromisoformat(state["waiting_since"])
                state["accumulated_secs"] = int((now - wait_start).total_seconds())
    return event


def _handle_moving_ping(ride_id, speed, now, state):
    event = "none"
    state["low_speed_since"] = None
    if state["is_waiting"]:
        if state["waiting_since"]:
            wait_start = datetime.fromisoformat(state["waiting_since"])
            state["accumulated_secs"] += int((now - wait_start).total_seconds())
        state["is_waiting"] = False
        state["waiting_since"] = None
        event = "waiting_ended"
        logger.info(
            f"Ride {ride_id}: WAITING ENDED. Total waiting={state['accumulated_secs']}s. Speed={speed:.2f}km/h"
        )
    return event
