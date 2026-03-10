# apps/drivers/tasks.py
"""
Celery tasks for driver metrics, scoring, and weekly resets.
Registered as periodic beats in settings.CELERY_BEAT_SCHEDULE.
"""

import logging

from celery import shared_task

from apps.common.backpressure import RetryStrategy
from apps.common.idempotency import idempotent_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
@idempotent_task(ttl=3600)
def recalculate_all_driver_scores(self):
    """
    Periodic: recalculate rates, composite score, and evaluate levels.
    """
    from apps.drivers.models import Driver
    from apps.drivers.services.level_engine import evaluate_level
    from apps.drivers.services.scoring import recalculate_driver_score

    drivers = Driver.objects.all()
    updated = 0

    for driver in drivers:
        try:
            recalculate_driver_score(driver)
            evaluate_level(driver)
            updated += 1
        except Exception as exc:
            countdown = RetryStrategy.get_countdown("NORMAL", self.request.retries)
            if countdown >= 0:
                self.retry(exc=exc, countdown=countdown)
            logger.error(f"Score recalc failed: {exc}")

    logger.info(f"recalculate_all_driver_scores: updated {updated} drivers")
    return updated


@shared_task(bind=True)
@idempotent_task(ttl=86400)
def reset_weekly_driver_stats(self):
    """
    Periodic: reset weekly_rides and peak_hour_rides every Monday at midnight.
    """
    from apps.drivers.models import DriverStats

    count = DriverStats.objects.update(weekly_rides=0, peak_hour_rides=0)
    logger.info(f"reset_weekly_driver_stats: reset {count} driver stat rows")
    return count


@shared_task(bind=True)
@idempotent_task(ttl=60)
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
                payload={
                    "message": "Your suspension has been lifted. You can go online again."
                },
            )
            lifted += 1
        except Exception as exc:
            logger.error(f"Failed to lift suspension for stats {stats.id}: {exc}")

    logger.info(f"lift_expired_suspensions: lifted {lifted} suspensions")
    return lifted


@shared_task(bind=True)
@idempotent_task(ttl=3600)
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
            logger.error(
                f"Cancellation nudge failed for driver {stats.driver_id}: {exc}"
            )

    logger.info(f"send_driver_feedback_nudges: sent {nudge_count} nudges")
    return nudge_count


def _is_ghost_session(last_seen, driver, now_ts, heartbeat_threshold):
    from django.utils import timezone

    if last_seen:
        return (now_ts - int(last_seen)) > heartbeat_threshold
    return (timezone.now() - driver.updated_at).total_seconds() > 600


def _cleanup_ghost_session(driver, last_seen):
    from apps.drivers.models import Driver
    from apps.drivers.redis import redis_client, remove_driver_from_geo

    logger.warning(
        f"Resilience: Pruning ghost session for Driver {driver.id} (Last Seen: {last_seen})",
        extra={"driver_id": driver.id},
    )
    driver.status = Driver.Status.OFFLINE
    driver.save(update_fields=["status", "updated_at"])
    remove_driver_from_geo(driver_id=driver.id)
    redis_client.delete(f"driver_socket:{driver.id}")


@shared_task
@idempotent_task(ttl=60)
def prune_ghost_driver_sessions():
    """
    SLA Resilience: Detects and disconnects drivers who have lost connectivity
    without properly disconnecting (ghost sessions).
    Runs every 2 minutes.
    """
    import time

    from apps.drivers.models import Driver
    from apps.drivers.redis import redis_client

    active_drivers = Driver.objects.filter(
        status__in=[Driver.Status.ONLINE, Driver.Status.BUSY]
    ).only("id", "user_id", "status", "updated_at")

    pruned_count = 0
    now_ts = int(time.time())
    HEARTBEAT_THRESHOLD = 300

    for driver in active_drivers:
        last_seen = redis_client.get(f"driver:{driver.id}:last_seen")
        if _is_ghost_session(last_seen, driver, now_ts, HEARTBEAT_THRESHOLD):
            try:
                _cleanup_ghost_session(driver, last_seen)
                pruned_count += 1
            except Exception as e:
                logger.error(f"Failed to prune driver {driver.id}: {e}")

    if pruned_count > 0:
        from apps.notifications.services.alerts import send_critical_alert

        send_critical_alert(
            title="Ghost Session Cleanup",
            message=f"Pruned {pruned_count} stale driver sessions to maintain system consistency.",
            level="INFO",
        )

    return f"Pruned {pruned_count} ghost driver sessions."
