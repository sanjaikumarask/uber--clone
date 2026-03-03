# apps/common/budget.py
import time
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class FailureBudget:
    """
    Global Failure Budget (SLO Enforcement).
    Prevents cascading failures by halting non-critical systems 
    if the error rate exceeds a 'budget' for a given window.
    """
    WINDOW = 300  # 5 minutes
    
    @classmethod
    def record_failure(cls, service: str):
        key = f"budget:fail:{service}"
        now = int(time.time())
        try:
            from apps.drivers.redis import redis_client as r
            pipe = r.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - cls.WINDOW)
            pipe.zcard(key)
            pipe.expire(key, cls.WINDOW * 2)
            _, _, count, _ = pipe.execute()
            return count
        except Exception:
            return 0

    @classmethod
    def is_exhausted(cls, service: str, limit: int = 100) -> bool:
        """
        If failures in 5m > limit, the budget is exhausted.
        Trigger: Switch to 'Degraded Mode' (e.g., skip expensive matching).
        """
        key = f"budget:fail:{service}"
        try:
            from apps.drivers.redis import redis_client as r
            count = r.zcount(key, int(time.time()) - cls.WINDOW, "+inf")
            if count >= limit:
                logger.critical(f"[SLO] Failure budget EXHAUSTED for {service} ({count}/{limit})")
                return True
            return False
        except Exception:
            return False
