from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.db import OperationalError
from django.http import HttpRequest, JsonResponse

from apps.common.adaptive import AdaptiveShedder
from apps.common.backpressure import RetryStrategy
from apps.common.circuit_breaker import CircuitOpenError, circuit_breaker
from apps.common.idempotency import IdempotencyMiddleware, idempotent_webhook
from apps.users.models import User


@pytest.mark.django_db
class TestReliabilityEngineering:
    """
    Advanced Reliability Suite: Focuses on cascading failure protection,
    adaptive shedding, and distributed consistency.
    """

    def setup_method(self):
        cache.clear()

    # ─── 1. CASCADING FAILURE PROTECTION (CIRCUIT BREAKER) ────────────────────

    def test_circuit_breaker_trip_and_bypass(self):
        """
        SCENARIO: External API Failure (e.g. Google Maps or Razorpay)
        Verify that after N failures, the circuit trips and stops hammering
        the downstream service.
        """
        service_name = "test_api"
        failure_threshold = 3

        @circuit_breaker(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=10,
        )
        def failing_api_call():
            raise ValueError("API Down")

        # 1. First 2 failures - Circuit remains CLOSED (tracking)
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_api_call()

        assert cache.get(f"circuit_fails_{service_name}") == 2
        assert cache.get(f"circuit_open_{service_name}") is None

        # 2. Third failure - Circuit TRIPS (OPEN)
        with pytest.raises(ValueError):
            failing_api_call()

        assert cache.get(f"circuit_open_{service_name}") is True

        # 3. Fourth call - Should Bypassed (CircuitOpenError) immediately
        # No more 'ValueError' because we don't even call the func.
        with pytest.raises(CircuitOpenError, match="Circuit Breaker OPEN"):
            failing_api_call()

    # ─── 2. SISTEM RELIABILITY (REDIS OUTAGE / FAIL-OPEN) ─────────────────────

    @patch("apps.common.idempotency.cache")
    def test_idempotency_middleware_fail_open_on_redis_outage(self, mock_cache):
        """
        SCENARIO: Redis Outage during HTTP request
        Idempotency is a 'nice-to-have' for safety, but it MUST NOT block
        the core application if Redis is down.
        """
        # Simulate Redis is DOWN (raises exception on every call)
        mock_cache.add.side_effect = Exception("Redis Connection Refused")
        mock_cache.get.side_effect = Exception("Redis Connection Refused")

        # Setup request
        request = HttpRequest()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "ref_123"}
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.id = 1

        # Identity function for get_response
        def get_response(req):
            return JsonResponse({"ok": True}, status=200)

        middleware = IdempotencyMiddleware(get_response)

        # EXECUTE: Middleware should catch the catch Exception and Fail-Open
        response = middleware(request)

        assert response.status_code == 200
        # Verify it actually asked Redis and didn't just skip the code path
        mock_cache.add.assert_called()

    # ─── 3. ADAPTIVE LOAD SHEDDING (QUEUED PRESSURE) ──────────────────────────

    def test_adaptive_load_shedding_priority(self):
        """
        SCENARIO: High System Load (Factor = 0.6)
        Verify that we shed LOW and NORMAL traffic while allowing HIGH and CRITICAL.
        """
        # 1. Set artificial high load
        cache.set(AdaptiveShedder.FACTOR_KEY, 0.6)

        # 2. Verify results
        assert AdaptiveShedder.should_shed("LOW") is True  # Limit 0.1 < 0.6
        assert AdaptiveShedder.should_shed("NORMAL") is True  # Limit 0.4 < 0.6
        assert AdaptiveShedder.should_shed("HIGH") is False  # Limit 0.8 > 0.6
        assert AdaptiveShedder.should_shed("CRITICAL") is False  # Limit 0.95 > 0.6

    # ─── 4. ASYNC TASK RELIABILITY (BACKOFF STRATEGY) ─────────────────────────

    def test_retry_exponential_backoff_jitter(self):
        """
        SCENARIO: Thundering Herd Prevention
        Verify that retries follow a capped exponential curve and incorporate jitter.
        """
        # CRITICAL priority: (10, 2, 60) -> base 2, max 60s
        times = []
        for _ in range(100):
            times.append(
                RetryStrategy.get_countdown("CRITICAL", attempt=3)
            )  # 2 * 2^3 = 16

        # 1. Jitter check (Results should be distributed)
        unique_times = set(times)
        assert len(unique_times) > 90  # High entropy due to jitter

        # 2. Caps check
        assert max(times) <= 16.0  # attempt 3 cap is base * 2^3

        # 3. Terminal retry check
        assert RetryStrategy.get_countdown("CRITICAL", attempt=11) == -1

    # ─── 5. DISTRIBUTED CONSISTENCY (WEBHOOK RACE) ───────────────────────────

    def test_webhook_concurrency_locking(self):
        """
        SCENARIO: Dual Webhook Delivery (Race Condition)
        If Razorpay delivers the same webhook twice in the same millisecond,
        one must be rejected with 429 TO prevent double-processing.
        """
        User.objects.create(username="webhook_user")

        @idempotent_webhook(provider="razorpay")
        def mock_webhook_view(request):
            return JsonResponse({"status": "ok"}, status=200)

        # Build mock request
        request = HttpRequest()
        request.headers = {"X-Razorpay-Event-Id": "evt_abc_789"}

        # 1. First execution - Mock Redis lock failure (concurrent run)
        with patch("apps.common.idempotency.cache.add") as mock_add:
            mock_add.return_value = False  # Signal: Lock already exists

            response = mock_webhook_view(request)

            assert response.status_code == 429
            data = response.content.decode()
            assert "Concurrent processing" in data

    # ─── 6. DB CONSISTENCY (LOCKED ENTITY HANDLING) ───────────────────────────

    @patch("django.db.models.query.QuerySet.select_for_update")
    def test_database_locking_contention_timeout(self, mock_select):
        """
        SCENARIO: DB Lock Contention
        Simulate a database OperationalError (Lock Timeout) and verify
        the application handles it via standard exception paths.
        """
        from apps.payments.tasks import process_driver_payout

        # 1. Simulate DB Lock Conflict
        mock_select.side_effect = OperationalError("could not obtain lock on row 123")

        # 2. Trigger task (this should hit the general exception block)
        # process_driver_payout uses RetryStrategy which is good practice.
        driver_id = 1
        with patch(
            "apps.drivers.models.Driver.objects.select_for_update"
        ) as mock_driver_select:
            mock_driver_select.side_effect = OperationalError("Lock Conflict")

            with patch("apps.payments.tasks.process_driver_payout.retry") as mock_retry:
                with patch(
                    "apps.common.backpressure.RetryStrategy.get_countdown",
                    return_value=5,
                ):
                    # Call the task. It should catch OperationalError and call retry because countdown > 0.
                    process_driver_payout(driver_id)
                    mock_retry.assert_called_once()
