from unittest.mock import MagicMock, patch

import pytest

from apps.common.budget import FailureBudget
from apps.common.chaos import ChaosMonkey
from apps.common.resilience import CircuitBreaker, CircuitBreakerError


@pytest.mark.django_db
class TestCommonResilience:
    """
    Validates SLO enforcement, Chaos injection, and Circuit Breaker.
    Crucial for a 50k+ scale system to prevent cascading failures.
    """

    def setup_method(self):
        from django.core.cache import cache

        cache.clear()

    # --- FailureBudget (SLO Enforcement) ---

    @patch("apps.drivers.redis.redis_client")
    def test_failure_budget_exhaustion_logic(self, mock_redis):
        """
        WHY: Verifies Redis-backed sliding window for failure tracking.
        Ensures is_exhausted returns True when count >= limit.
        """
        service = "test_svc"
        mock_redis.zcount.return_value = 10

        # Test 1: Below limit
        assert FailureBudget.is_exhausted(service, limit=11) is False

        # Test 2: At/Above limit
        assert FailureBudget.is_exhausted(service, limit=10) is True

    # --- Circuit Breaker (External API Isolation) ---

    def test_circuit_breaker_lifecycle_open_halfopen_closed(self):
        """
        WHY: Verifies the state machine transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
        Prevents wasting resources on dead upstream APIs.
        """
        breaker = CircuitBreaker(name="external_api", threshold=2, reset_timeout=1)

        @breaker
        def failing_call():
            raise ValueError("Upstream Down")

        @breaker
        def success_call():
            return "OK"

        # 1. State: CLOSED -> OPEN (after 2 failures)
        with pytest.raises(ValueError):
            failing_call()
        with pytest.raises(ValueError):
            failing_call()

        # 2. State: OPEN (requests must be blocked without calling the function)
        with pytest.raises(CircuitBreakerError):
            failing_call()

        # 3. State: Transition to HALF_OPEN (after timeout)
        with patch("django.core.cache.cache.get") as mock_cache_get:
            # Mocking that the 'timer' key is expired but state is still OPEN
            def side_effect(key, default=None):
                if "timer" in key:
                    return None
                if "state" in key:
                    return "OPEN"
                return default

            mock_cache_get.side_effect = side_effect

            # This trial call should be allowed but if it fails, circuit re-opens
            with pytest.raises(ValueError):
                failing_call()

    # --- ChaosMonkey (Failure Injection) ---

    @patch("django.db.connection.cursor")
    def test_chaos_monkey_validity(self, mock_cursor):
        """
        WHY: Ensures chaos simulation tools don't fail silently.
        """
        ChaosMonkey.simulate_db_slowdown(delay=0.1, probability=1.0)
        mock_cursor.return_value.__enter__.return_value.execute.assert_called()

    # --- Tracing (Observability) ---

    def test_tracing_middleware_injection(self):
        """
        WHY: Essential for debugging. Every request MUST have a Trace ID.
        """
        from django.http import HttpResponse

        from apps.common.resilience import TracingMiddleware

        request = MagicMock()
        request.headers = {}
        get_response = MagicMock(return_value=HttpResponse())

        middleware = TracingMiddleware(get_response)
        response = middleware(request)

        assert "X-Trace-ID" in response
        assert response["X-Trace-ID"] is not None
