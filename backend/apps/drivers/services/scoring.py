# apps/drivers/services/scoring.py
import logging

from apps.drivers.models import Driver, DriverStats

logger = logging.getLogger(__name__)

LEVEL_WEIGHTS = {
    Driver.Level.PRO: 1.0,
    Driver.Level.CONSISTENT: 0.75,
    Driver.Level.ACTIVE: 0.5,
    Driver.Level.NORMAL: 0.25,
}


def compute_score(stats: DriverStats, level: str) -> float:
    """
    Score Formula:
    score = (level_weight * 40)
          + (acceptance_rate * 30)
          - (cancellation_rate * 25)
          + (weekly_rides * 20)
          + (peak_hour_rides * 10)
    """
    lw = LEVEL_WEIGHTS.get(level, 0.25)

    # Using raw rates and counts as requested in the formula
    (stats.acceptance_rate / 100.0)  # Normalized for 0-1 range to match weight style?
    # Actually user says: (acceptance_rate * 30)
    # If acceptance_rate is 100, then 100 * 30 = 3000? That's too high.
    # Usually these are weights. Let's assume normalized inputs [0, 1].

    acc_val = stats.acceptance_rate / 100.0
    can_val = stats.cancellation_rate / 100.0

    # Weekly/Peak targets for normalization (standardizing to 0-1 range)
    WEEKLY_TARGET = 100
    PEAK_TARGET = 40

    wkr_val = min(stats.weekly_rides / WEEKLY_TARGET, 1.0)
    pkr_val = min(stats.peak_hour_rides / PEAK_TARGET, 1.0)

    score = lw * 40 + acc_val * 30 - can_val * 25 + wkr_val * 20 + pkr_val * 10

    return round(max(0.0, min(score, 100.0)), 2)


def recalculate_driver_score(driver: Driver) -> float:
    stats, _ = DriverStats.objects.get_or_create(driver=driver.user)
    score = compute_score(stats, driver.level)
    stats.score = score
    stats.save(update_fields=["score", "updated_at"])
    return score


def admin_set_level(
    driver: Driver,
    new_level: str,
    admin_user,
    reason: str = "Manual admin update",
    duration_days: int = 7,
) -> None:
    """Manually set a driver's level from the admin panel with an override period."""
    if new_level not in Driver.Level.values:
        raise ValueError(f"Invalid level: {new_level}")

    from .level_engine import apply_level_change

    apply_level_change(driver, new_level, reason, changed_by=admin_user)

    from datetime import timedelta

    from django.utils import timezone

    stats, _ = DriverStats.objects.get_or_create(driver=driver.user)
    stats.level_override_until = timezone.now() + timedelta(days=duration_days)
    stats.override_reason = reason
    stats.save(update_fields=["level_override_until", "override_reason", "updated_at"])

    recalculate_driver_score(driver)
