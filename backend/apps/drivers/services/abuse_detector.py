# apps/drivers/services/abuse_detector.py
"""
Anti-Abuse Detection Engine
============================

Detects two main patterns:
1. Accept-Cancel cycling: driver accepts then cancels rapidly many times.
2. Fake ride behaviour: driver completes ride in unrealistically short time
   or with zero distance.

Penalties are progressive:
  1st offence  → 30-min block
  2nd offence  → 2-hour block
  3rd+ offence → 24-hour block AND platform alert
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.drivers.models import Driver, DriverStats

logger = logging.getLogger(__name__)

# Thresholds
ACCEPT_CANCEL_WINDOW_MINUTES = 60  # Look back 60 min
ACCEPT_CANCEL_THRESHOLD = 3  # 3 quick accept-then-cancel within window
MIN_RIDE_COMPLETION_SECONDS = 60  # Ride completed in less than 60s → suspicious
MIN_RIDE_DISTANCE_KM = 0.1  # Distance below 0.1 km → suspicious


BLOCK_DURATIONS = [
    timedelta(minutes=30),
    timedelta(hours=2),
    timedelta(hours=24),
]


def _get_block_duration(offence_count: int) -> timedelta:
    idx = min(offence_count - 1, len(BLOCK_DURATIONS) - 1)
    return BLOCK_DURATIONS[idx]


def _apply_block(driver: Driver, stats: DriverStats, reason: str) -> None:
    offence_count = getattr(stats, "fraud_flags_count", 0) + 1
    stats.fraud_flags_count = offence_count
    duration = _get_block_duration(offence_count)

    stats.is_suspended = True
    stats.suspended_until = timezone.now() + duration
    stats.trust_score = max(0.0, stats.trust_score - 15.0)
    stats.save(
        update_fields=[
            "fraud_flags_count",
            "is_suspended",
            "suspended_until",
            "trust_score",
            "updated_at",
        ]
    )

    driver.status = Driver.Status.BLOCKED
    driver.save(update_fields=["status", "updated_at"])

    logger.warning(
        f"[ABUSE] Driver {driver.id} BLOCKED for {duration}. "
        f"Offence #{offence_count}. Reason: {reason}"
    )

    # Notify driver
    try:
        from apps.notifications.models import Notification

        until_str = stats.suspended_until.strftime("%H:%M %d %b")
        Notification.objects.create(
            user=driver.user,
            channel="push",
            type="ACCOUNT_BLOCKED",
            payload={
                "message": f"Your account has been temporarily blocked until {until_str} due to suspicious activity.",
                "reason": reason,
                "until": stats.suspended_until.isoformat(),
            },
        )
    except Exception:
        pass

    # Critical alert for 3rd+ offence
    if offence_count >= 3:
        try:
            from apps.notifications.services.alerts import send_critical_alert

            send_critical_alert(
                title="Repeat Offender – Manual Review Required",
                message=f"Driver {driver.user.get_full_name() or driver.id} has {offence_count} abuse flags. Blocked 24h.",
                level="CRITICAL",
            )
        except Exception:
            pass


@transaction.atomic
def check_accept_cancel_abuse(driver: Driver) -> bool:
    """
    Look at this driver's last hour of ride history.
    If they accepted then cancelled ≥ threshold rides → flag.
    Returns True if abuse detected.
    """
    from apps.rides.models import Ride

    window_start = timezone.now() - timedelta(minutes=ACCEPT_CANCEL_WINDOW_MINUTES)

    cancel_count = Ride.objects.filter(
        driver=driver,
        status=Ride.Status.CANCELLED,
        cancelled_by=Ride.CancelledBy.DRIVER,
        updated_at__gte=window_start,
    ).count()

    if cancel_count >= ACCEPT_CANCEL_THRESHOLD:
        stats, _ = DriverStats.objects.select_for_update().get_or_create(driver=driver)
        _apply_block(
            driver,
            stats,
            f"Accept-cancel cycling detected ({cancel_count} cancellations in 1h)",
        )
        return True

    return False


@transaction.atomic
def check_fake_ride(driver: Driver, ride) -> bool:
    """
    Called after a ride is completed.
    Returns True if ride looks fake.
    """
    suspicious = False
    reason_parts = []

    if ride.start_time and ride.end_time:
        duration_s = (ride.end_time - ride.start_time).total_seconds()
        if duration_s < MIN_RIDE_COMPLETION_SECONDS:
            suspicious = True
            reason_parts.append(f"completed in {duration_s:.0f}s")

    dist = getattr(ride, "actual_distance_km", None)
    if dist is not None and float(dist) < MIN_RIDE_DISTANCE_KM:
        suspicious = True
        reason_parts.append(f"distance {dist} km")

    if suspicious:
        stats, _ = DriverStats.objects.select_for_update().get_or_create(driver=driver)
        stats.fraud_flags_count = (stats.fraud_flags_count or 0) + 1
        reason = "Fake ride: " + ", ".join(reason_parts)
        _apply_block(driver, stats, reason)
        logger.warning(
            f"[FAKE-RIDE] Ride {ride.id} flagged. Driver {driver.id}. {reason}"
        )
        return True

    return False
