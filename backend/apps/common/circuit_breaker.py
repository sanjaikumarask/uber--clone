import logging
from functools import wraps

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    pass


def circuit_breaker(
    service_name: str, failure_threshold: int = 5, recovery_timeout: int = 60
):
    """
    Production-grade Network Circuit Breaker.
    Prevents cascading internal failures by instantly rejecting requests
    to a third-party service if it fails continuously.
    Automatically resets connection attempts after recovery_timeout.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            fail_key = f"circuit_fails_{service_name}"
            open_key = f"circuit_open_{service_name}"

            # 1. State: OPEN (Tripped)
            # If the circuit is explicitly marked open, block calls instantly
            if cache.get(open_key):
                raise CircuitOpenError(
                    f"Circuit Breaker OPEN for {service_name}. Bypassing external call."
                )

            try:
                # Execute the network call
                result = func(*args, **kwargs)

                # 2. State: RESET (Success)
                # If it succeeds, clear any tracking failures (circuit closes)
                cache.delete(fail_key)
                return result

            except Exception as e:
                # 3. State: FAILURE TRACKING
                fails = cache.get(fail_key, 0) + 1
                cache.set(fail_key, fails, timeout=recovery_timeout * 2)

                logger.warning(
                    f"Circuit Breaker ({service_name}) failure {fails}/{failure_threshold}: {e}"
                )

                if fails >= failure_threshold:
                    # Trip the breaker -> Transition to OPEN state
                    logger.critical(
                        f"🛑 CIRCUIT BREAKER TRIPPED for {service_name}! Freezing calls for {recovery_timeout}s."
                    )
                    cache.set(open_key, True, timeout=recovery_timeout)
                    from apps.notifications.services.alerts import send_critical_alert

                    send_critical_alert(
                        title=f"Circuit Breaker Tripped: {service_name}",
                        message=f"The {service_name} API has failed {failure_threshold} consecutive times. Traffic is now halted for {recovery_timeout} seconds to allow recovery.",
                        level="CRITICAL",
                    )

                # Re-raise the actual error
                raise

        return wrapper

    return decorator
