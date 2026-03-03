# apps/common/chaos.py
import time
import random
import logging
from django.db import connection

logger = logging.getLogger(__name__)

class ChaosMonkey:
    """
    Simulation utility for Chaos Testing at 50k+ scale.
    Use ONLY in staging environments.
    """
    
    @classmethod
    def simulate_db_slowdown(cls, delay: float = 2.0, probability: float = 0.1):
        """Simulates intermittent database latency."""
        if random.random() < probability:
            logger.error(f"[Chaos] Injecting DB latency: {delay}s")
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT pg_sleep({delay})")

    @classmethod
    def simulate_redis_outage(cls, probability: float = 0.05):
        """Forces a Redis connection failure to test 'fail-open' logic."""
        if random.random() < probability:
            logger.critical("[Chaos] Simulating Redis ConnectionError")
            from redis.exceptions import ConnectionError
            raise ConnectionError("Chaos Monkey forced Redis offline")

    @classmethod
    def simulate_retry_storm(cls, endpoint: str):
        """Simulates 1000 duplicated requests to test idempotency and throttling."""
        logger.warning(f"[Chaos] Simulating retry storm on {endpoint}")
        # Logic to fire multiple mock requests...
        pass
