# apps/drivers/services/metrics.py
import logging

from django.utils import timezone

from apps.drivers.models import Driver, DriverStats

logger = logging.getLogger(__name__)


def update_driver_metrics(driver: Driver, event_type: str):
    """
    Update driver metrics in real-time based on ride events.
    Synchronously triggers score and level evaluation.
    """
    stats, _ = DriverStats.objects.get_or_create(driver=driver)
    stats.last_active_at = timezone.now()

    update_fields = ["last_active_at", "updated_at"]

    if event_type == "OFFERED":
        stats.offered_rides += 1
        update_fields.append("offered_rides")

    elif event_type == "ACCEPTED":
        stats.accepted_rides += 1
        update_fields.append("accepted_rides")

    elif event_type == "CANCELLED":
        stats.cancelled_rides += 1
        update_fields.append("cancelled_rides")

    elif event_type == "COMPLETED":
        stats.completed_rides += 1
        stats.total_rides += 1
        stats.weekly_rides += 1
        if timezone.now().hour in {7, 8, 9, 17, 18, 19, 20}:  # Peak hours
            stats.peak_hour_rides += 1
        update_fields.extend(
            ["completed_rides", "total_rides", "weekly_rides", "peak_hour_rides"]
        )

    elif event_type == "REJECTED":
        stats.check_and_reset_daily_stats()
        stats.rejection_count_today += 1
        update_fields.append("rejection_count_today")

    elif event_type == "NO_SHOW":
        stats.no_shows += 1
        update_fields.append("no_shows")

    # Recalculate rates
    if stats.offered_rides > 0:
        stats.acceptance_rate = round(
            (stats.accepted_rides / stats.offered_rides) * 100, 2
        )
        update_fields.append("acceptance_rate")

    if stats.accepted_rides > 0:
        stats.cancellation_rate = round(
            (stats.cancelled_rides / stats.accepted_rides) * 100, 2
        )
        update_fields.append("cancellation_rate")

    stats.save(update_fields=update_fields)

    # Trigger Score & Level Evaluation
    from .level_engine import evaluate_level
    from .scoring import recalculate_driver_score

    recalculate_driver_score(driver)
    evaluate_level(driver)
