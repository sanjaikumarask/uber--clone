# apps/drivers/services/trust.py

from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from apps.drivers.models import DriverStats


SUSPEND_NO_SHOWS = 3
SUSPEND_CANCEL_RATE = 0.4
SUSPEND_DURATION_MINUTES = 30


@transaction.atomic
def register_completed_ride(driver):
    stats, _ = DriverStats.objects.select_for_update().get_or_create(driver=driver)
    stats.total_rides += 1
    stats.completed_rides += 1
    stats.save(update_fields=["total_rides", "completed_rides", "updated_at"])


@transaction.atomic
def register_driver_cancellation(driver):
    stats, _ = DriverStats.objects.select_for_update().get_or_create(driver=driver)
    stats.total_rides += 1
    stats.cancelled_rides += 1
    stats.save(update_fields=["total_rides", "cancelled_rides", "updated_at"])
    _evaluate_penalty(stats)


@transaction.atomic
def register_no_show(driver):
    stats, _ = DriverStats.objects.select_for_update().get_or_create(driver=driver)
    stats.no_shows += 1
    stats.save(update_fields=["no_shows", "updated_at"])
    _evaluate_penalty(stats)


def _evaluate_penalty(stats: DriverStats):
    cancel_rate = (
        stats.cancelled_rides / stats.total_rides
        if stats.total_rides else 0
    )

    if stats.no_shows >= SUSPEND_NO_SHOWS or cancel_rate >= SUSPEND_CANCEL_RATE:
        stats.is_suspended = True
        stats.suspended_until = timezone.now() + timedelta(
            minutes=SUSPEND_DURATION_MINUTES
        )
        stats.save(
            update_fields=["is_suspended", "suspended_until", "updated_at"]
        )
