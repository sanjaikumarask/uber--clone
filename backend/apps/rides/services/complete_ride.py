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
from apps.rides.services.realtime import persist_ride_history_to_db

logger = logging.getLogger(__name__)


def complete_ride(ride_id: int) -> Ride:
    """
    Marks a ride as COMPLETED, calculates final fare, and broadcasts
    to all interested parties via the lifecycle service.

    IDEMPOTENT: if the ride is already COMPLETED, returns it unchanged.
    """
    # ── Step 0: Sync buffered tracking data from Redis to Postgres ─────
    # This must happen before we calculate the final fare to ensure distance is accurate.
    try:
        persist_ride_history_to_db(ride_id)
    except Exception as e:
        logger.error(f"Failed to persist ride history for {ride_id}: {e}")

    with transaction.atomic():
        ride = (
            Ride.objects.select_for_update(of=("self",))
            .select_related("driver", "rider")
            .get(id=ride_id)
        )

        # ── Guard: already completed ──────────────────────────────────────
        if ride.status == Ride.Status.COMPLETED:
            logger.warning(f"complete_ride({ride_id}): already COMPLETED — skipping")
            return ride

        # ── Step 1: Pull GPS waiting time from Redis ───────────────────────
        try:
            from apps.rides.services.waiting_detector import (
                clear_waiting_state,
                get_total_waiting_seconds,
            )

            gps_waiting_seconds = get_total_waiting_seconds(ride_id)

            # Use GPS waiting only if it's MORE than what lifecycle already locked
            if gps_waiting_seconds > ride.waiting_seconds:
                ride.waiting_seconds = gps_waiting_seconds
                ride.save(update_fields=["waiting_seconds"])

            logger.info(
                f"complete_ride({ride_id}): waiting_seconds={ride.waiting_seconds}s"
            )
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

        # ── Step 2.5: ADVANCED FRAUD DETECTION ───────────────────────────────
        try:
            from apps.common.fraud import apply_fraud_penalties, run_fraud_checks

            fraud_signals = run_fraud_checks(ride)
            if fraud_signals:
                ride.is_fraud_flagged = True
                ride.save(update_fields=["is_fraud_flagged"])
                apply_fraud_penalties(ride, fraud_signals)
                logger.warning(
                    f"[FraudEngine] Ride {ride.id} flagged: {fraud_signals}",
                    extra={"ride_id": ride.id, "driver_id": ride.driver_id},
                )
        except Exception as e:
            logger.error(f"[FraudEngine] Check failed for ride {ride.id}: {e}")

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
