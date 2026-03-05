# apps/common/fraud.py
"""
Advanced Fraud Detection Engine.

Beyond velocity-based GPS spoofing (already in driver_location.py),
this module handles pattern-level fraud that requires cross-ride analysis:

  1. Repeat Short-Ride Farming   — driver repeatedly creates sub-1km rides
     to collect per-ride incentives.
  2. Route Manipulation           — driver intentionally takes a longer
     route to inflate distance-based fare.
  3. Frequency Anomaly            — driver completes an implausible number
     of rides in a rolling time window.
  4. Pickup-Dropoff Proximity Trap — driver accepts a ride, immediately
     marks "arrived", and completes within seconds (ghost ride).
  5. Coordinated Abuse            — same rider+driver pair repeatedly within 24h.
"""
import logging
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# ─── Thresholds (tune per city/vehicle-type) ─────────────────────────────────
REPEAT_PAIR_LIMIT       = 3     # Same rider+driver in 24h → suspicious
MAX_RIDES_PER_HOUR      = 6     # > 6 completed rides/hour is physically impossible
GHOST_RIDE_SECONDS      = 90    # Trip start→end in < 90s = ghost ride
MIN_VALID_DURATION_SECS = 60    # Any ride shorter than 1 min is suspicious
ROUTE_INFLATION_RATIO   = 2.0   # actual_km > 2x planned_km = inflation attempt
MAX_SPEED_KMH           = 150.0 # Any movement > 150km/h in city is suspicious (Spoofing)
MIN_PING_INTERVAL       = 5     # Minimum seconds between GPS pings to trust velocity calc


# ─── 1. GHOST RIDE DETECTION ─────────────────────────────────────────────────

def detect_ghost_ride(ride) -> bool:
    """
    Returns True if the ride looks like a ghost/fake ride.
    A ghost ride: OTP verified → completed in < 90 seconds.
    """
    if not ride.start_time or not ride.completed_at:
        return False

    duration = (ride.completed_at - ride.start_time).total_seconds()
    if duration < GHOST_RIDE_SECONDS:
        logger.warning(
            f"[Fraud] Ghost ride detected: ride={ride.id} "
            f"duration={duration:.0f}s driver={ride.driver_id}",
            extra={"ride_id": ride.id, "driver_id": ride.driver_id}
        )
        return True
    return False


# ─── 2. ROUTE INFLATION DETECTION ────────────────────────────────────────────

def detect_route_inflation(ride) -> bool:
    """
    Returns True if the driver drove significantly further than the planned route.
    Actual > 2x planned is a strong signal of intentional detour.
    Already partially checked in complete_ride.py (2.5x), this checks at 2.0x
    to create a soft-flag before the final hard-flag.
    """
    if not ride.actual_distance_km or not ride.planned_distance_km:
        return False
    if ride.planned_distance_km < 0.5:   # Skip very short planned routes
        return False

    ratio = ride.actual_distance_km / ride.planned_distance_km
    if ratio > ROUTE_INFLATION_RATIO:
        logger.warning(
            f"[Fraud] Route inflation: ride={ride.id} "
            f"actual={ride.actual_distance_km:.2f}km "
            f"planned={ride.planned_distance_km:.2f}km "
            f"ratio={ratio:.2f}x",
            extra={"ride_id": ride.id, "driver_id": ride.driver_id}
        )
        return True
    return False


# ─── 3. FREQUENCY ANOMALY ────────────────────────────────────────────────────

def detect_frequency_anomaly(driver) -> bool:
    """
    Checks if a driver completed an implausible number of rides in the last hour.
    > 6 completed rides/hour is physically impossible (avg ride > 10 min).
    """
    from apps.rides.models import Ride
    one_hour_ago = timezone.now() - timedelta(hours=1)
    count = Ride.objects.filter(
        driver=driver,
        status=Ride.Status.COMPLETED,
        completed_at__gte=one_hour_ago,
    ).count()

    if count > MAX_RIDES_PER_HOUR:
        logger.warning(
            f"[Fraud] Frequency anomaly: driver={driver.id} "
            f"completed {count} rides in last hour",
            extra={"driver_id": driver.id}
        )
        return True
    return False


# ─── 4. COORDINATED ABUSE (Same Rider+Driver Pair) ───────────────────────────

def detect_coordinated_abuse(driver, ride) -> bool:
    """
    Detects when the same driver-rider pair repeats rides suspiciously
    often (e.g. round-tripping to farm incentives).
    """
    from apps.rides.models import Ride
    yesterday = timezone.now() - timedelta(hours=24)
    count = Ride.objects.filter(
        driver=driver,
        rider=ride.rider,
        status=Ride.Status.COMPLETED,
        completed_at__gte=yesterday,
    ).count()

    if count >= REPEAT_PAIR_LIMIT:
        logger.warning(
            f"[Fraud] Coordinated abuse: driver={driver.id} "
            f"rider={ride.rider_id} rides={count} in 24h",
            extra={"ride_id": ride.id, "driver_id": driver.id}
        )
        return True
    return False


# ─── 5. GPS VELOCITY GUARD (SPOOFING DETECTION) ─────────────────────────────

def validate_gps_velocity(driver_id, new_lat, new_lng):
    """
    Detects GPS Spoofing/Teleportation by calculating speed between pings.
    If speed > 150km/h, it is physically impossible in city traffic.
    """
    from apps.drivers.redis import redis_client
    import time
    from geopy.distance import geodesic

    meta_key = f"driver:{driver_id}:meta"
    last_data = redis_client.hgetall(meta_key)
    
    if not last_data or "lat" not in last_data or "lng" not in last_data:
        # First ping, just store and return
        redis_client.hset(meta_key, mapping={"lat": new_lat, "lng": new_lng, "last_seen": int(time.time())})
        return True

    last_lat = float(last_data["lat"])
    last_lng = float(last_data["lng"])
    last_time = int(last_data["last_seen"])
    now = int(time.time())

    time_diff = now - last_time
    # 🚨 RESILIENCE FIX: If last ping was > 5 mins ago, reset velocity tracking.
    # Prevents false "teleportation" flags when driver re-opens app in a new location.
    if time_diff > 300:
        logger.info(f"[SPOOF] Resetting velocity tracking for Driver {driver_id} (Stale data: {time_diff}s)")
        redis_client.hset(meta_key, mapping={"lat": new_lat, "lng": new_lng, "last_seen": now})
        return True

    if time_diff < MIN_PING_INTERVAL:
        return True # Too frequent pings, skip velocity check to avoid noise

    # Calculate distance in km
    dist_km = geodesic((last_lat, last_lng), (new_lat, new_lng)).km
    
    # Calculate speed (km/h)
    speed_kmh = (dist_km / time_diff) * 3600

    if speed_kmh > MAX_SPEED_KMH:
        logger.critical(
            f"[SPOOF] GPS Teleportation detected for Driver {driver_id}! "
            f"Speed: {speed_kmh:.1f} km/h, Distance: {dist_km:.2f} km in {time_diff}s"
        )
        # Record fraud signal for the session
        redis_client.hincrby(f"driver:{driver_id}:fraud", "spoof_count", 1)
        return False

    # Update last valid position
    redis_client.hset(meta_key, mapping={"lat": new_lat, "lng": new_lng, "last_seen": now})
    return True


# ─── 5. COMPOSITE ENTRY POINT ────────────────────────────────────────────────

def run_fraud_checks(ride) -> list[str]:
    """
    Runs all fraud detectors on ride completion.
    Returns a list of triggered fraud signals.
    Caller is responsible for flagging the ride and alerting.

    Usage in complete_ride.py:
        signals = run_fraud_checks(ride)
        if signals:
            ride.is_fraud_flagged = True
            ...
    """
    signals = []
    driver  = ride.driver
    if not driver:
        return signals

    if detect_ghost_ride(ride):
        signals.append("GHOST_RIDE")

    if detect_route_inflation(ride):
        signals.append("ROUTE_INFLATION")

    if detect_frequency_anomaly(driver):
        signals.append("FREQUENCY_ANOMALY")

    if detect_coordinated_abuse(driver, ride):
        signals.append("COORDINATED_ABUSE")

    return signals


def apply_fraud_penalties(ride, signals: list[str]):
    """
    Applies trust score penalties and conditionally blocks the driver.
    Called after run_fraud_checks returns non-empty signals.
    """
    from apps.drivers.models import DriverStats
    from apps.notifications.services.alerts import send_critical_alert

    try:
        stats = ride.driver.stats
    except Exception:
        return

    PENALTY_MAP = {
        "GHOST_RIDE":          10.0,
        "ROUTE_INFLATION":     8.0,
        "FREQUENCY_ANOMALY":   5.0,
        "COORDINATED_ABUSE":   7.0,
    }

    total_penalty = sum(PENALTY_MAP.get(s, 5.0) for s in signals)
    stats.trust_score    = max(0.0, stats.trust_score - total_penalty)
    stats.fraud_flags_count += 1
    stats.save(update_fields=["trust_score", "fraud_flags_count", "updated_at"])

    # Hard suspension at trust score < 30
    if stats.trust_score < 30.0:
        ride.driver.status = "BLOCKED"
        ride.driver.save(update_fields=["status"])

    send_critical_alert(
        title=f"Fraud Detected: Driver #{ride.driver_id}",
        message=(
            f"Ride #{ride.id} | Signals: {', '.join(signals)}\n"
            f"Trust score: {stats.trust_score:.1f} | "
            f"Total flags: {stats.fraud_flags_count}"
        ),
        level="CRITICAL" if stats.trust_score < 30.0 else "ERROR"
    )
