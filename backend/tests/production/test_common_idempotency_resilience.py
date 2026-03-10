import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

from apps.common.idempotency import (
    IdempotencyMiddleware,
    idempotent_task,
    idempotent_webhook,
)


@pytest.mark.django_db
class TestCommonIdempotencyResilience:
    """
    Validation for Idempotency logic across HTTP, Celery, and Webhook layers.
    Increases apps/common/idempotency.py coverage (currently 51%).
    """

    def setup_method(self):
        cache.clear()

    # --- 1. Middleware Replay & Lock ---

    def test_middleware_replays_cached_response(self):
        """
        WHY: Network Resilience. Ensures that if a client retries a request
        due to a timeout, they get the SAME successfully processed response.
        """
        MagicMock()
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "key_123"}
        request.user.is_authenticated = True
        request.user.id = 1

        # 1. First request succeeds
        resp_data = {"id": 101, "status": "created"}
        get_response = MagicMock(return_value=JsonResponse(resp_data, status=201))

        middleware = IdempotencyMiddleware(get_response)
        response1 = middleware(request)
        assert response1.status_code == 201

        # 2. Duplicate request is REPLAYED from cache
        get_response_2 = MagicMock()  # Should NOT be called
        middleware_2 = IdempotencyMiddleware(get_response_2)
        response2 = middleware_2(request)

        assert response2.status_code == 201
        assert json.loads(response2.content) == resp_data
        get_response_2.assert_not_called()

    def test_middleware_fail_open_on_redis_timeout(self):
        """
        WHY: Availability Guard. If Redis is down, we must still process
        payments even if we lose idempotency guarantees (better than 500 error).
        """
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "key_fails"}
        request.user.is_authenticated = False

        get_response = MagicMock(
            return_value=HttpResponse("Real Execution", status=200)
        )

        with patch(
            "django.core.cache.cache.add", side_effect=Exception("Redis Timeout")
        ):
            middleware = IdempotencyMiddleware(get_response)
            response = middleware(request)

            assert response.status_code == 200
            assert response.content == b"Real Execution"

    # --- 2. Celery Task Idempotency ---

    def test_idempotent_task_concurrent_race_prevention(self):
        """
        WHY: Preventing Double Settlement. If two workers pick up the same
        payout task simultaneously, Only ONE must execute.
        """
        mock_func = MagicMock(return_value="SUCCESS")
        task = idempotent_task(ttl=60)(mock_func)

        # Simulate 'Phase 1: RUNNING lock' acquired by another thread
        with patch("django.core.cache.cache.add", return_value=False):
            result = task(ride_id=55)
            assert result is None
            mock_func.assert_not_called()

    # --- 3. Webhook Deduplication ---

    def test_idempotent_webhook_deduplication(self):
        """
        WHY: Webhook reliability. Razorpay often sends the same event 3+ times.
        We must ingest only once to prevent multiple ledger entries.
        """
        handler = MagicMock(return_value=JsonResponse({"status": "ok"}, status=200))
        webhook = idempotent_webhook(provider="razorpay")(handler)

        request = MagicMock()
        request.headers = {"X-Razorpay-Event-Id": "evt_unique_999"}

        # 1. Ingest
        resp1 = webhook(request)
        assert resp1.status_code == 200

        # 2. Duplicate (Re-fetched from cache)
        with patch("django.core.cache.cache.get", return_value="1"):
            resp2 = webhook(request)
            assert resp2.status_code == 200
            assert json.loads(resp2.content)["status"] == "already_processed"
            assert handler.call_count == 1  # Only called for FIRST request
