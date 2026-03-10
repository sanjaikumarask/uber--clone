import logging
import secrets

from django.db import connection

logger = logging.getLogger(__name__)
_cryptogen = secrets.SystemRandom()


class ChaosMonkey:
    """
    Simulation utility for Chaos Testing at 50k+ scale.
    Use ONLY in staging environments.
    """

    @classmethod
    def simulate_db_slowdown(cls, delay: float = 2.0, probability: float = 0.1):
        """Simulates intermittent database latency."""
        if _cryptogen.random() < probability:
            logger.error(f"[Chaos] Injecting DB latency: {delay}s")
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_sleep(%s)", [delay])

    @classmethod
    def simulate_redis_outage(cls, probability: float = 0.05):
        """Forces a Redis connection failure to test 'fail-open' logic."""
        if _cryptogen.random() < probability:
            logger.critical("[Chaos] Simulating Redis ConnectionError")
            from redis.exceptions import ConnectionError as RedisConnectionError

            raise RedisConnectionError("Chaos Monkey forced Redis offline")

    @classmethod
    def simulate_retry_storm(cls, endpoint: str):
        """Simulates 1000 duplicated requests to test idempotency and throttling."""
        # Logic to fire multiple mock requests...
