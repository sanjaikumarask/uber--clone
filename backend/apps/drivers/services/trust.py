# apps/drivers/services/trust.py
import logging
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from apps.drivers.models import Driver, DriverStats
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)

def apply_progressive_suspension(driver: Driver, stats: DriverStats):
    """
    Suspension Durations: 30m, 2h, 24h
    Increments fraud_flags_count as violation counter.
    """
    if stats.is_suspended and stats.suspended_until > timezone.now():
        return

    current_flags = int(getattr(stats, 'fraud_flags_count', 0))
    stats.fraud_flags_count = current_flags + 1
    
    durations = [
        timedelta(minutes=30),
        timedelta(hours=2),
        timedelta(hours=24)
    ]
    
    # Select duration based on fraud_flags_count (violations)
    idx = min(stats.fraud_flags_count - 1, len(durations) - 1)
    duration = durations[idx]
    
    stats.is_suspended = True
    stats.suspended_until = timezone.now() + duration
    stats.save(update_fields=["is_suspended", "suspended_until", "fraud_flags_count", "updated_at"])
    
    # Force Offline is better for UX, BLOCKED is for permanent bans.
    # But for progressive suspension, setting to OFFLINE + is_suspended=True is sufficient.
    driver.status = Driver.Status.OFFLINE
    driver.save(update_fields=["status", "updated_at"])
    
    Notification.objects.create(
        user=driver.user,
        channel="ws",
        type="ACCOUNT_SUSPENDED",
        payload={
            "title": "Account Suspended",
            "message": f"Your account is suspended for {duration} due to excessive violations.",
            "suspended_until": stats.suspended_until.isoformat()
        }
    )
    logger.warning(f"Driver {driver.id} suspended for {duration} (Violation #{stats.fraud_flags_count})")

def register_completed_ride(driver: Driver):
    """Signals a successful ride completion. Updates metrics and rewards trust."""
    from .metrics import update_driver_metrics
    # update_driver_metrics handles increments for total_rides and completed_rides
    update_driver_metrics(driver, "COMPLETED")

def register_driver_cancellation(driver: Driver):
    """Registers a driver-side cancellation and checks for penalty thresholds."""
    from .metrics import update_driver_metrics
    with transaction.atomic():
        # 1. Update core metrics (this handles cancellation_rate calculation)
        update_driver_metrics(driver, "CANCELLED")
        
        # 2. Re-fetch stats to check triggers
        stats = DriverStats.objects.select_for_update().get(driver=driver)
        
        # 3. Check for penalty: > 40% cancellation rate if they have enough history
        # metrics.py calculates cancellation_rate as (cancelled / accepted) * 100
        if stats.accepted_rides >= 5 and stats.cancellation_rate > 40:
            apply_progressive_suspension(driver, stats)

def register_no_show(driver: Driver):
    """Registers a passenger no-show (driver arrived but rider didn't show)."""
    from .metrics import update_driver_metrics
    with transaction.atomic():
        # 1. Update core metrics
        update_driver_metrics(driver, "NO_SHOW")
        
        # 2. Re-fetch stats
        stats = DriverStats.objects.select_for_update().get(driver=driver)
        
        # 3. Suspend on 3rd no-show
        if stats.no_shows >= 3:
            apply_progressive_suspension(driver, stats)
