# apps/common/backpressure.py
"""
Backpressure Control for 10k+ Concurrent Users.

Failure modes addressed:
  - Reconnect Storm: 5,000 drivers disconnect simultaneously (network blip)
    and all reconnect in the same 200ms window → Redis/DB saturated.
  - Retry Flood: Mobile clients hammer accept/complete endpoints on 503.
  - Celery Queue Saturation: retry_matching fires 15k tasks in 15s.

Strategies:
  1. ConnectionRateLimiter     — WebSocket connect rate per driver (sliding window).
  2. EndpointThrottle          — Per-user API cooldown via Redis sliding window.
  3. CeleryQueueDepthGuard     — Skips scheduling if the queue is already deep.
  4. ExponentialBackoffJitter  — Calculates server-side retry delay with jitter.
"""
import time
import random
import logging
from django.core.cache import cache
from apps.notifications.services.alerts import send_critical_alert

logger = logging.getLogger(__name__)


# ─── 1. WEBSOCKET RECONNECT RATE LIMITER ──────────────────────────────────────

class ConnectionRateLimiter:
    """
    Sliding-window rate limiter for WebSocket connections.
    Prevents individual drivers from hammering the connect endpoint
    during reconnect storms (e.g. app crash-loop).

    Default: max 5 reconnects per 60 seconds per driver.
    """
    WINDOW   = 60    # seconds
    MAX_HITS = 5     # max reconnects in window

    @classmethod
    def is_allowed(cls, driver_id: int) -> bool:
        key    = f"ws:rate:{driver_id}"
        now    = int(time.time())
        window = now - cls.WINDOW

        # Redis ZADD + ZREMRANGEBYSCORE sliding window
        from django.core.cache import caches
        try:
            from apps.drivers.redis import redis_client as r
            # Add current timestamp as both score and member
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window)       # Evict old entries
            pipe.zadd(key, {str(now): now})             # Add current
            pipe.zcard(key)                             # Count in window
            pipe.expire(key, cls.WINDOW * 2)
            _, _, count, _ = pipe.execute()

            if count > cls.MAX_HITS:
                logger.warning(
                    f"[Backpressure] WS reconnect flood: driver_id={driver_id} "
                    f"attempts={count} in {cls.WINDOW}s"
                )
                send_critical_alert(
                    title="WS Connect Storm Detected",
                    message=f"Driver {driver_id} attempted {count} reconnects in {cls.WINDOW}s. Throttling active.",
                    level="WARNING"
                )
                return False
            return True
        except Exception as exc:
            logger.error(f"[Backpressure] Rate limiter Redis error: {exc}")
            return True  # Fail open


# ─── 2. API ENDPOINT THROTTLE (per-user sliding window) ────────────────────────

def endpoint_cooldown(user_id, endpoint: str, max_calls: int = 10, window: int = 10, priority: str = "NORMAL") -> bool:
    """
    Adaptive SLIDING WINDOW throttle.
    Dynamically adjusts 'max_calls' based on the global shedding factor.
    """
    from apps.common.adaptive import AdaptiveShedder
    if AdaptiveShedder.should_shed(priority=priority):
        return False

    key = f"throttle:{endpoint}:{user_id}"
    now = int(time.time())
    
    # Adaptive factor: Decrease the effective capacity as system load increases
    factor = AdaptiveShedder.get_factor()
    effective_max = int(max_calls * (1.0 - factor))
    if effective_max < 1: effective_max = 1

    try:
        from apps.drivers.redis import redis_client as r
        # Use a more unique member to allow multiple requests in same second
        member = f"{now}:{random.getrandbits(32)}"
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, window * 2)
        _, _, count, _ = pipe.execute()

        if count > effective_max:
            return False
        return True
    except Exception:
        return True


# ─── 3. CELERY QUEUE DEPTH GUARD ─────────────────────────────────────────────

class CeleryQueueGuard:
    """
    Prevents scheduling new tasks if the target queue is already saturated.
    Caps queue depth based on priority to prevent system lockup.
    """
    QUEUE_LIMITS = {
        "high":   10000,
        "medium": 5000,
        "low":    2000,
    }

    @classmethod
    def can_enqueue(cls, queue_name: str = "medium") -> bool:
        from apps.common.adaptive import AdaptiveShedder
        if AdaptiveShedder.should_shed(priority=queue_name.upper()):
            return False

        try:
            from apps.drivers.redis import redis_client as r
            depth = r.llen(queue_name)
            limit = cls.QUEUE_LIMITS.get(queue_name, 5000)
            
            if depth > limit:
                logger.warning(f"[Backpressure] Queue {queue_name} saturated (depth={depth})")
                return False
            return True
        except Exception:
            return True # Fail open


# ─── 4. RETRY STRATEGY ────────────────────────────────────────────────────────

class RetryStrategy:
    """
    Centralised, priority-aware retry calculator.

    Priority:  CRITICAL > HIGH > NORMAL > LOW
    All retries use full jitter to prevent synchronized retry floods:
        delay = random(0, min(cap, base * 2^attempt))

    References: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """
    CONFIGS = {
        # (max_retries, base_s, cap_s)
        "CRITICAL": (10, 2,   60),   # Payout settle — retries up to ~1 min cap
        "HIGH":     (6,  5,   300),  # Reconciliation — retries up to ~5 min cap
        "NORMAL":   (4,  15,  600),  # Matching retry — up to 10 min
        "LOW":      (3,  60,  1800), # Feedback nudges — up to 30 min
    }

    @classmethod
    def get_countdown(cls, priority: str, attempt: int) -> float:
        """
        Returns the next retry delay in seconds for the given priority and attempt number.
        Uses full-jitter exponential backoff.
        """
        max_retries, base, cap = cls.CONFIGS.get(priority, cls.CONFIGS["NORMAL"])
        if attempt >= max_retries:
            return -1  # Signal: no more retries

        exp_delay = base * (2 ** attempt)
        capped    = min(cap, exp_delay)
        # Full jitter: random between 0 and the capped delay
        jitter    = random.uniform(0, capped)
        return round(jitter, 2)

    @classmethod
    def get_max_retries(cls, priority: str) -> int:
        return cls.CONFIGS.get(priority, cls.CONFIGS["NORMAL"])[0]
