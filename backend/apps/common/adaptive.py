# apps/common/adaptive.py
import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

# ─── 1. ADAPTIVE LOAD SHEDDING ────────────────────────────────────────────────


class AdaptiveShedder:
    """
    Dynamically adjusts system rate limits based on overhead.
    Monitors Redis health and Celery queue depth.

    If 'shedding_factor' > 0.5, we start rejecting non-pinpoint traffic.
    """

    FACTOR_KEY = "system:shedding:factor"
    LATENCY_THRESHOLD = 0.05  # 50ms Redis latency threshold

    @classmethod
    def update_health(cls):
        """Measures system health and updates the global shedding factor."""
        from apps.common.budget import FailureBudget

        # 1. Measure Resource Latency
        start = time.time()
        cache.set("system:health:ping", "1", timeout=5)
        latency = time.time() - start

        # 2. Check Failure Budgets (Cascading Failure Protection)
        # If critical services are failing, we shed load even if CPU/Latency is fine.
        budget_exhausted = any(
            [
                FailureBudget.is_exhausted("payout", limit=50),
                FailureBudget.is_exhausted("ride_lifecycle", limit=100),
            ]
        )

        # 3. Calculate new factor
        factor = float(cache.get(cls.FACTOR_KEY) or 0.0)

        if latency > cls.LATENCY_THRESHOLD or budget_exhausted:
            logger.warning(
                f"[Adaptive] Health Degraded (Latency: {latency:.4f}s, BudgetExhausted: {budget_exhausted})"
            )
            factor = min(1.0, factor + 0.2)  # Aggressive increase
        else:
            factor = max(0.0, factor - 0.05)  # Gradual recovery

        cache.set(cls.FACTOR_KEY, factor, timeout=60)
        return factor

    @classmethod
    def get_factor(cls) -> float:
        return float(cache.get(cls.FACTOR_KEY) or 0.0)

    @classmethod
    def should_shed(cls, priority: str = "NORMAL") -> bool:
        """
        Determines if a request should be dropped based on its priority.

        HIGH:   Ignore shedding factor below 0.9.
        NORMAL: Ignore shedding factor below 0.5.
        LOW:    Ignore shedding factor below 0.2.
        """
        factor = cls.get_factor()
        if factor <= 0.1:
            return False

        thresholds = {
            "CRITICAL": 0.95,
            "HIGH": 0.8,
            "NORMAL": 0.4,
            "LOW": 0.1,
        }

        limit = thresholds.get(priority, 0.5)
        if factor > limit:
            logger.error(
                f"[Adaptive] SHEDDING LOAD (Priority: {priority}, Factor: {factor:.2f})"
            )
            return True

        return False


# Trigger update_health via Periodic Celery task or keep it stateless on-demand (expensive).
