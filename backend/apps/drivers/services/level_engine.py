# apps/drivers/services/level_engine.py
import logging
from django.utils import timezone
from datetime import timedelta
from apps.drivers.models import Driver, DriverStats, DriverLevelHistory
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)

def evaluate_level(driver: Driver):
    """
    Evaluates and applies driver level changes based on performance metrics.
    Includes Promotion, Downgrade, and Inactivity rules.
    """
    stats, _ = DriverStats.objects.get_or_create(driver=driver)
    
    # 1. Handle Admin Overrides
    if stats.is_level_overridden:
        logger.info(f"Driver {driver.id} has active admin override until {stats.level_override_until}")
        return

    old_level = driver.level
    new_level = Driver.Level.NORMAL
    reason = "SYSTEM"

    # 2. Promotion Logic (Evaluated High to Low)
    if (stats.weekly_rides >= 100 and 
        stats.acceptance_rate >= 90 and 
        stats.cancellation_rate < 10):
        new_level = Driver.Level.PRO
        reason = "AUTO_PROMOTION"
        
    elif (stats.weekly_rides >= 50 and 
          stats.acceptance_rate >= 80):
        new_level = Driver.Level.CONSISTENT
        reason = "AUTO_PROMOTION"
        
    elif stats.weekly_rides >= 20:
        new_level = Driver.Level.ACTIVE
        reason = "AUTO_PROMOTION"
    
    # 3. Downgrade Overrides
    inactivity_period = timezone.now() - stats.last_active_at
    if inactivity_period > timedelta(days=7):
        new_level = Driver.Level.NORMAL
        reason = "INACTIVITY_DOWNGRADE"
    elif stats.acceptance_rate < 60 or stats.cancellation_rate > 25:
        # Penalties force a downgrade from current if not already NORMAL
        if old_level == Driver.Level.PRO:
            new_level = Driver.Level.CONSISTENT
        elif old_level == Driver.Level.CONSISTENT:
            new_level = Driver.Level.ACTIVE
        elif old_level == Driver.Level.ACTIVE:
            new_level = Driver.Level.NORMAL
        reason = "PERFORMANCE_DOWNGRADE"

    # 4. Apply Changes
    if new_level != old_level:
        apply_level_change(driver, new_level, reason)
        
    # 5. Penalty Check (Suspension)
    if stats.cancellation_rate > 30:
        trigger_suspension(driver, stats)
    
    # 6. Performance Warnings
    check_performance_warnings(driver, stats)

def check_performance_warnings(driver: Driver, stats: DriverStats):
    """Sends nudges for low acceptance or high cancellation."""
    if 60 <= stats.acceptance_rate < 75:
        Notification.objects.create(
            user=driver.user, channel="ws", type="DRIVER_FEEDBACK",
            payload={"title": "Low Acceptance", "message": "Your acceptance rate is dropping. Accept more rides to maintain your level."}
        )
    
    if 15 < stats.cancellation_rate <= 25:
        Notification.objects.create(
            user=driver.user, channel="ws", type="DRIVER_FEEDBACK",
            payload={"title": "High Cancellation", "message": "Your cancellation rate is high. This may lead to a level downgrade."}
        )

def apply_level_change(driver: Driver, new_level: str, reason: str, changed_by=None):
    old_level = driver.level
    driver.level = new_level
    driver.save(update_fields=["level", "updated_at"])
    
    DriverLevelHistory.objects.create(
        driver=driver,
        old_level=old_level,
        new_level=new_level,
        reason=reason,
        changed_by=changed_by
    )
    
    # Trigger Feedback
    Notification.objects.create(
        user=driver.user,
        channel="ws",
        type="LEVEL_CHANGED",
        payload={
            "title": "Level Updated",
            "message": f"Your driver level is now {new_level} due to {reason}.",
            "new_level": new_level
        }
    )

def trigger_suspension(driver: Driver, stats: DriverStats):
    """Progressive suspension logic."""
    from apps.drivers.services.trust import apply_progressive_suspension
    apply_progressive_suspension(driver, stats)
