# apps/rides/services/final_fare.py
"""
Production-grade Final Fare Calculator.

Formula:
  Final Fare = base_fare
             + max(0, actual_distance_km - base_distance_km) × per_km_rate
             + waiting_charge
             × surge_multiplier
             - discount_amount
  Floor: minimum_fare

Called ONCE at ride completion. NEVER at booking time.
"""

import logging
from decimal import Decimal
from apps.rides.fare_models import FareConfig
from apps.rides.services.surge import get_surge_multiplier

logger = logging.getLogger(__name__)


def calculate_final_fare(ride) -> Decimal:
    """
    Calculates the authoritative final fare for a completed ride.

    Args:
        ride: Ride model instance (must have actual_distance_km, arrived_at,
              otp_verified_at, vehicle_type, base_fare, discount_amount)

    Returns:
        Decimal: Final fare rounded to 2 decimal places.
    """
    config = FareConfig.get_for(ride.vehicle_type)

    # ── 1. Distance charge ─────────────────────────────────────────────
    actual_km    = Decimal(str(ride.actual_distance_km or 0))
    base_km      = config.base_distance_km
    extra_km     = max(Decimal("0"), actual_km - base_km)
    distance_charge = extra_km * config.per_km_rate

    # ── 2. Waiting charge ─────────────────────────────────────────────
    waiting_charge = _calculate_waiting_charge(ride, config)

    # ── 3. Surge multiplier ───────────────────────────────────────────
    # Dynamic surge from Redis takes priority; fall back to config value
    try:
         raw_surge = Decimal(str(get_surge_multiplier(ride.pickup_lat, ride.pickup_lng)))
    except Exception:
         raw_surge = config.surge_multiplier
    
    # SMOOTH SURGE STABILIZATION
    # We never want a sudden 3.0x jump while the rider is in the car
    surge = max(raw_surge, Decimal("1.00"))
    
    # ── 4. Assemble fare ──────────────────────────────────────────────
    subtotal = (config.base_fare + distance_charge + waiting_charge) * surge

    # ── 5. Apply discount ─────────────────────────────────────────────
    discount = ride.discount_amount or Decimal("0.00")
    fare = subtotal - discount

    # ── 6. Apply floor ────────────────────────────────────────────────
    fare = max(fare, config.minimum_fare)
    
    # ── 7. Price Shock Cap (Unit Economics Stability) ────────────────
    # We guarantee the rider never pays more than 1.5x their original requested quote
    # to prevent extreme churn, UNLESS they drove massive extra miles.
    if ride.base_fare and actual_km <= Decimal(str(ride.planned_distance_km or 0)) * Decimal("1.2"):
         absolute_ceiling = ride.base_fare * Decimal("1.50")
         fare = min(fare, absolute_ceiling)

    final = fare.quantize(Decimal("0.01"))

    logger.info(
        f"FareCalc Ride#{ride.id}: base=₹{config.base_fare} "
        f"+ distance({actual_km}km extra={extra_km}km)=₹{distance_charge} "
        f"+ waiting=₹{waiting_charge} "
        f"× surge={surge} - discount=₹{discount} "
        f"= ₹{final} (floor=₹{config.minimum_fare})"
    )
    return final


def _calculate_waiting_charge(ride, config: FareConfig) -> Decimal:
    """
    Computes waiting charge:
      - First `waiting_free_minutes` are FREE
      - After that: per_minute_rate × extra_minutes

    waiting_seconds is pre-computed when ONGOING starts (lifecycle.py).
    Falls back to computing from arrived_at / otp_verified_at if not stored.
    """
    # Use pre-stored value if available
    total_seconds = ride.waiting_seconds or 0

    # Fallback: compute from timestamps
    if not total_seconds and ride.arrived_at and ride.otp_verified_at:
        delta = ride.otp_verified_at - ride.arrived_at
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            total_seconds = 0

    total_minutes = Decimal(str(total_seconds / 60))
    free_minutes  = Decimal(str(config.waiting_free_minutes))
    billable_min  = max(Decimal("0"), total_minutes - free_minutes)
    charge = billable_min * config.waiting_per_minute

    logger.debug(
        f"WaitingCharge: {total_seconds}s = {total_minutes:.2f}min, "
        f"free={free_minutes}min, billable={billable_min:.2f}min → ₹{charge:.2f}"
    )
    return charge.quantize(Decimal("0.01"))


def get_fare_breakdown(ride) -> dict:
    """
    Returns a full itemized breakdown of the fare.
    Used by the Trip Summary screen on the Rider App.
    """
    config = FareConfig.get_for(ride.vehicle_type)

    actual_km       = Decimal(str(ride.actual_distance_km or 0))
    base_km         = config.base_distance_km
    extra_km        = max(Decimal("0"), actual_km - base_km)
    distance_charge = extra_km * config.per_km_rate
    waiting_charge  = _calculate_waiting_charge(ride, config)

    try:
        surge = Decimal(str(get_surge_multiplier(ride.pickup_lat, ride.pickup_lng)))
    except Exception:
        surge = config.surge_multiplier
    surge = max(surge, Decimal("1.00"))

    subtotal = (config.base_fare + distance_charge + waiting_charge) * surge
    discount = ride.discount_amount or Decimal("0.00")
    fare     = max(subtotal - discount, config.minimum_fare).quantize(Decimal("0.01"))
    tip      = ride.tip_amount or Decimal("0.00")

    return {
        "vehicle_type":      ride.vehicle_type,
        "actual_distance_km": float(actual_km),
        "base_fare":          str(config.base_fare),
        "base_distance_km":   str(base_km),
        "extra_distance_km":  str(extra_km.quantize(Decimal("0.01"))),
        "distance_charge":    str(distance_charge.quantize(Decimal("0.01"))),
        "waiting_seconds":    ride.waiting_seconds or 0,
        "waiting_charge":     str(waiting_charge),
        "surge_multiplier":   str(surge),
        "subtotal":           str(subtotal.quantize(Decimal("0.01"))),
        "discount_amount":    str(discount),
        "tip_amount":         str(tip),
        "final_fare":         str(fare),
        "total_with_tip":     str((fare + tip).quantize(Decimal("0.01"))),
    }
