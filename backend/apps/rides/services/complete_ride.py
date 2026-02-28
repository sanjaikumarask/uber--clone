# apps/rides/services/complete_ride.py
"""
Ride completion service.
  1. Pull accumulated waiting_seconds from GPS detector (Redis)
  2. Calculate final fare (FareConfig + distance + waiting)
  3. Transition status → COMPLETED (broadcasts + earnings + payment record)
  4. Clean up Redis waiting state
"""

import logging
from django.db import transaction
from apps.rides.models import Ride

logger = logging.getLogger(__name__)


def complete_ride(ride_id: int) -> Ride:
    """
    Marks a ride as COMPLETED, calculates final fare, and broadcasts
    to all interested parties via the lifecycle service.

    IDEMPOTENT: if the ride is already COMPLETED, returns it unchanged.
    """
    with transaction.atomic():
        ride = Ride.objects.select_for_update(of=("self",)).select_related("driver", "rider").get(id=ride_id)

        # ── Guard: already completed ──────────────────────────────────────
        if ride.status == Ride.Status.COMPLETED:
            logger.warning(f"complete_ride({ride_id}): already COMPLETED — skipping")
            return ride

        # ── Step 1: Pull GPS waiting time from Redis ───────────────────────
        try:
            from apps.rides.services.waiting_detector import (
                get_total_waiting_seconds,
                clear_waiting_state,
            )
            gps_waiting_seconds = get_total_waiting_seconds(ride_id)

            # Use GPS waiting only if it's MORE than what lifecycle already locked
            if gps_waiting_seconds > ride.waiting_seconds:
                ride.waiting_seconds = gps_waiting_seconds
                ride.save(update_fields=["waiting_seconds"])

            logger.info(f"complete_ride({ride_id}): waiting_seconds={ride.waiting_seconds}s")
        except Exception as e:
            logger.warning(f"complete_ride({ride_id}): waiting detector error ({e})")

        # ── Step 2: Calculate final fare ──────────────────────────────────
        from .final_fare import calculate_final_fare, get_fare_breakdown
        ride.final_fare = calculate_final_fare(ride)
        
        # Snapshot the fare math components
        try:
            ride.fare_breakdown = get_fare_breakdown(ride)
        except Exception as e:
            logger.error(f"Failed to generate fare breakdown for {ride.id}: {e}")
        # ── Step 2.5: FRAUD DETECTION CHECKS ──────────────────────────────
        if ride.actual_distance_km and ride.planned_distance_km:
            if ride.actual_distance_km > ride.planned_distance_km * 2.5:
                # Driver drove 2.5x further than expected
                ride.is_fraud_flagged = True
        
        if ride.waiting_seconds and ride.waiting_seconds > 3600:
            # Driver waited over 1 entire hour
            ride.is_fraud_flagged = True
            
        if getattr(ride, "is_fraud_flagged", False):
            logger.warning(f"🚨 FRAUD FLAG RAISED inside completion for Ride {ride.id}")
            from apps.notifications.services.alerts import send_critical_alert
            send_critical_alert(
                title=f"Fraud Flag Triggered: Ride #{ride.id}",
                message=f"Driver {ride.driver.first_name} completed a ride that vastly exceeded distance or wait thresholds. Payout distributions have been frozen.",
                level="CRITICAL"
            )
            
            # Algorithmic Trust Penalty
            if ride.driver:
                stats = getattr(ride.driver, 'stats', None)
                if stats:
                    stats.fraud_flags_count += 1
                    stats.trust_score = max(0.0, stats.trust_score - 5.0)  # -5 Points per severe violation
                    stats.save(update_fields=["fraud_flags_count", "trust_score"])
                    
                    if stats.trust_score < 40.0:
                        # Auto-Suspend
                        ride.driver.status = "BLOCKED"
                        ride.driver.save(update_fields=["status"])
                        send_critical_alert(
                            title=f"Auto-Suspension Issued",
                            message=f"Driver {ride.driver.first_name} organically dropped below 40.0 Trust Score. Account automatically BLOCKED.",
                            level="CRITICAL"
                        )

        ride.save(update_fields=["final_fare", "fare_breakdown", "is_fraud_flagged"])

        logger.info(f"complete_ride({ride_id}): final_fare=₹{ride.final_fare}")

        # ── Step 3: Status COMPLETED + all broadcasts ─────────────────────
        from .lifecycle import update_ride_status
        update_ride_status(ride, Ride.Status.COMPLETED)

        # ── Step 4: Driver metrics — completed ride ───────────────────────
        if ride.driver:
            from apps.drivers.services.metrics import update_driver_metrics
            update_driver_metrics(ride.driver, "COMPLETED")

            # Anti-abuse: fake ride detection
            from apps.drivers.services.abuse_detector import check_fake_ride
            check_fake_ride(ride.driver, ride)
            
            # DRIVER INCENTIVES
            from apps.driver_incentives.services import apply_driver_incentive
            apply_driver_incentive(ride)

        # RIDER OFFERS
        from apps.offers.services.offer_engine import OfferEngine
        OfferEngine.finalize_usage(ride)

        # ── Step 5: Clean up Redis ─────────────────────────────────────────
        try:
            clear_waiting_state(ride_id)
        except Exception:
            pass  # Non-critical

        return ride