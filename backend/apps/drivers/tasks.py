# apps/drivers/tasks.py
"""
Celery tasks for driver metrics, scoring, and weekly resets.
Registered as periodic beats in settings.CELERY_BEAT_SCHEDULE.
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def recalculate_all_driver_scores(self):
    """
    Periodic: recalculate rates, composite score, and evaluate levels.
    """
    from apps.drivers.models import Driver
    from apps.drivers.services.scoring import recalculate_driver_score
    from apps.drivers.services.level_engine import evaluate_level

    drivers = Driver.objects.all()
    updated = 0

    for driver in drivers:
        try:
            recalculate_driver_score(driver)
            evaluate_level(driver)
            updated += 1
        except Exception as exc:
            logger.error(f"Score recalc failed for driver {driver.id}: {exc}")

    logger.info(f"recalculate_all_driver_scores: updated {updated} drivers")
    return updated


@shared_task(bind=True, max_retries=3)
def reset_weekly_driver_stats(self):
    """
    Periodic: reset weekly_rides and peak_hour_rides every Monday at midnight.
    """
    from apps.drivers.models import DriverStats

    count = DriverStats.objects.update(weekly_rides=0, peak_hour_rides=0)
    logger.info(f"reset_weekly_driver_stats: reset {count} driver stat rows")
    return count


@shared_task(bind=True, max_retries=3)
def lift_expired_suspensions(self):
    """
    Periodic (every 5 min): unsuspend drivers whose suspension window has passed.
    """
    from django.utils import timezone
    from apps.drivers.models import Driver, DriverStats

    now = timezone.now()
    expired = DriverStats.objects.filter(is_suspended=True, suspended_until__lte=now)

    lifted = 0
    for stats in expired:
        try:
            stats.is_suspended = False
            stats.save(update_fields=["is_suspended", "updated_at"])

            driver = stats.driver
            if driver.status == Driver.Status.BLOCKED:
                driver.status = Driver.Status.OFFLINE
                driver.save(update_fields=["status", "updated_at"])

            # Notify driver they are unblocked
            from apps.notifications.models import Notification
            Notification.objects.create(
                user=driver.user,
                channel="push",
                type="SUSPENSION_LIFTED",
                payload={"message": "Your suspension has been lifted. You can go online again."},
            )
            lifted += 1
        except Exception as exc:
            logger.error(f"Failed to lift suspension for stats {stats.id}: {exc}")

    logger.info(f"lift_expired_suspensions: lifted {lifted} suspensions")
    return lifted


@shared_task(bind=True, max_retries=3)
def send_driver_feedback_nudges(self):
    """
    Periodic (daily): push real-time feedback messages to drivers with
    low acceptance or high cancellation rates.
    """
    from apps.drivers.models import DriverStats
    from apps.notifications.models import Notification

    nudge_count = 0

    # Low acceptance nudge
    low_acc = DriverStats.objects.filter(
        acceptance_rate__lt=70.0,
        offered_rides__gte=5,  # Only nudge if they have meaningful sample size
    ).select_related("driver__user")

    for stats in low_acc:
        try:
            payload = {
                "title": "Improve Your Acceptance Rate",
                "message": (
                    f"Your acceptance rate is {stats.acceptance_rate:.0f}%. "
                    "Accepting more rides helps you earn more and maintain your driver level."
                ),
                "category": "acceptance_low",
            }
            # Push channel
            Notification.objects.create(
                user=stats.driver.user,
                channel="push",
                type="DRIVER_FEEDBACK",
                payload=payload,
            )
            # Websocket channel
            Notification.objects.create(
                user=stats.driver.user,
                channel="ws",
                type="DRIVER_FEEDBACK",
                payload=payload,
            )
            nudge_count += 1
        except Exception as exc:
            logger.error(f"Nudge failed for driver {stats.driver_id}: {exc}")

    # High cancellation nudge
    high_can = DriverStats.objects.filter(
        cancellation_rate__gt=15.0,
        accepted_rides__gte=5,
    ).select_related("driver__user")

    for stats in high_can:
        try:
            payload = {
                "title": "Avoid Cancellations",
                "message": (
                    f"Your cancellation rate is {stats.cancellation_rate:.0f}%. "
                    "Frequent cancellations can lead to temporary suspension."
                ),
                "category": "cancellation_high",
            }
            # Push
            Notification.objects.create(
                user=stats.driver.user,
                channel="push",
                type="DRIVER_FEEDBACK",
                payload=payload,
            )
            # Websocket
            Notification.objects.create(
                user=stats.driver.user,
                channel="ws",
                type="DRIVER_FEEDBACK",
                payload=payload,
            )
            nudge_count += 1
        except Exception as exc:
            logger.error(f"Cancellation nudge failed for driver {stats.driver_id}: {exc}")

    logger.info(f"send_driver_feedback_nudges: sent {nudge_count} nudges")
    return nudge_count
