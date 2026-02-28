# apps/drivers/services/trust.py
import logging
from django.utils import timezone
from datetime import timedelta
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

    stats.fraud_flags_count += 1
    
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
    
    driver.status = Driver.Status.BLOCKED
    driver.save(update_fields=["status", "updated_at"])
    
    Notification.objects.create(
        user=driver.user,
        channel="ws",
        type="ACCOUNT_SUSPENDED",
        payload={
            "title": "Account Suspended",
            "message": f"Your account is suspended for {duration} due to excessive cancellations.",
            "suspended_until": stats.suspended_until.isoformat()
        }
    )
    logger.warning(f"Driver {driver.id} suspended for {duration} (Violation #{stats.fraud_flags_count})")
