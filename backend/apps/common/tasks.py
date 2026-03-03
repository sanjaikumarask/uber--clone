# apps/common/tasks.py
import logging
from celery import shared_task
from apps.common.chaos import ChaosMonkey
from apps.common.adaptive import AdaptiveShedder

logger = logging.getLogger(__name__)

@shared_task
def run_chaos_simulation():
    """
    Background Task for Continuous Chaos Engine.
    Injects random failures to ensure the system's self-healing 
    and fail-open mechanisms are working under 50k+ user load.
    """
    logger.warning("[ChaosTask] Starting scheduled stability test.")
    
    # Simulate partial DB slowdown (20% probability)
    ChaosMonkey.simulate_db_slowdown(delay=1.5, probability=0.2)
    
    # Simulate intermittent Redis connectivity (5% probability)
    # This specifically tests if our RateLimiters and Shedders fail-open.
    try:
        ChaosMonkey.simulate_redis_outage(probability=0.05)
    except Exception as e:
        logger.error(f"[ChaosTask] Redis Outage Simulation Successful: {e}")

@shared_task
def update_system_health():
    """
    Periodic task to update the Adaptive Shedding factor.
    Should run every 10-30 seconds.
    """
    factor = AdaptiveShedder.update_health()
    logger.debug(f"[Adaptive] Periodic health check. Current shedding factor: {factor:.2f}")
