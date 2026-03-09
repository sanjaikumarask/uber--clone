import json
import pytest
from unittest.mock import MagicMock, patch
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from rest_framework import status

from apps.common.idempotency import (
    IdempotencyMiddleware,
    idempotent_task,
    idempotent_webhook,
    idempotent_request
)

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()

class TestIdempotencyMiddleware:

    def test_non_mutating_request(self):
        get_response = MagicMock(return_value=HttpResponse("ok"))
        middleware = IdempotencyMiddleware(get_response)
        
        request = MagicMock()
        request.method = "GET"
        
        response = middleware(request)
        assert response.content == b"ok"
        get_response.assert_called_once()

    def test_mutating_no_key(self):
        get_response = MagicMock(return_value=HttpResponse("ok"))
        middleware = IdempotencyMiddleware(get_response)
        
        request = MagicMock()
        request.method = "POST"
        request.headers = {}
        
        response = middleware(request)
        assert response.content == b"ok"
        get_response.assert_called_once()

    def test_first_request_success(self, user):
        get_response = MagicMock(return_value=JsonResponse({"status": "created"}, status=201))
        middleware = IdempotencyMiddleware(get_response)
        
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "unique-key-1"}
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 201
        assert json.loads(response.content) == {"status": "created"}
        
        # Verify it's cached
        cached = cache.get(f"idem:api:{user.id}:unique-key-1")
        assert cached["status"] == 201
        assert cached["data"] == {"status": "created"}

    def test_replay_cached_response(self, user):
        # Setup cache
        cache_key = f"idem:api:{user.id}:unique-key-2"
        cache.set(cache_key, {"status": 201, "data": {"replayed": True}}, timeout=3600)
        
        get_response = MagicMock()
        middleware = IdempotencyMiddleware(get_response)
        
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "unique-key-2"}
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 201
        assert json.loads(response.content) == {"replayed": True}
        get_response.assert_not_called()

    def test_concurrent_request_conflict(self, user):
        # Setup IN_FLIGHT
        cache_key = f"idem:api:{user.id}:unique-key-3"
        cache.set(cache_key, "IN_FLIGHT", timeout=60)
        
        get_response = MagicMock()
        middleware = IdempotencyMiddleware(get_response)
        
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "unique-key-3"}
        request.user = user
        
        response = middleware(request)
        assert response.status_code == 409
        get_response.assert_not_called()

class TestIdempotentTask:

    def test_task_executes_once(self):
        mock_func = MagicMock(return_value="result")
        decorated = idempotent_task(ttl=3600)(mock_func)
        
        # First execution
        res1 = decorated("arg1", kw="val")
        assert res1 == "result"
        assert mock_func.call_count == 1
        
        # Second execution (same args)
        res2 = decorated("arg1", kw="val")
        assert res2 is None
        assert mock_func.call_count == 1

    @patch("apps.common.idempotency.cache.add")
    def test_task_concurrent_blocked(self, mock_add):
        mock_add.return_value = False # Simulate lock exists
        mock_func = MagicMock()
        decorated = idempotent_task(ttl=3600)(mock_func)
        
        res = decorated("arg")
        assert res is None
        mock_func.assert_not_called()

class TestIdempotentWebhook:

    def test_webhook_deduplication(self):
        mock_view = MagicMock(return_value=HttpResponse("ok", status=200))
        decorated = idempotent_webhook(provider="razorpay")(mock_view)
        
        request = MagicMock()
        request.headers = {"X-Razorpay-Event-Id": "evt_123"}
        
        # First call
        resp1 = decorated(request)
        assert resp1.status_code == 200
        assert mock_view.call_count == 1
        
        # Second call
        resp2 = decorated(request)
        assert resp2.status_code == 200
        assert json.loads(resp2.content) == {"status": "already_processed"}
        assert mock_view.call_count == 1

    def test_webhook_concurrent_conflict(self):
        mock_view = MagicMock(return_value=HttpResponse("ok"))
        decorated = idempotent_webhook(provider="razorpay")(mock_view)
        
        request = MagicMock()
        request.headers = {"X-Razorpay-Event-Id": "evt_456"}
        
        # Setup lock manually
        cache.set("idem:webhook:lock:razorpay:evt_456", "1", timeout=60)
        
        resp = decorated(request)
        assert resp.status_code == 429
        mock_view.assert_not_called()

class TestIdempotentRequestDecorator:

    def test_decorator_success(self, user):
        view = MagicMock(return_value=JsonResponse({"done": True}, status=200))
        decorated = idempotent_request(ttl=3600)(view)
        
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-Idempotency-Key": "key-abc"}
        request.user = user
        
        # First call
        resp1 = decorated(None, request)
        assert resp1.status_code == 200
        assert view.call_count == 1
        
        # Second call
        resp2 = decorated(None, request)
        assert resp2.status_code == 200
        assert json.loads(resp2.content) == {"done": True}
        assert view.call_count == 1
