# apps/common/idempotency.py
"""
Global Idempotency System.

Three distinct enforcement points:

  1. IdempotencyMiddleware — HTTP layer.  Replays cached responses for
     any POST/PUT/PATCH with X-Idempotency-Key header.  Prevents double-
     clicks, network retries, and mobile reconnect storms.

  2. @idempotent_task — Celery task layer.  Ensures a task body executes
     at most once for a given set of arguments within a TTL window.
     Critical for: settle_driver_payout, reconcile_pending_payments.

  3. @idempotent_webhook — Webhook handler layer.  Uses Razorpay's native
     X-Razorpay-Event-Id to deduplicate at ingestion time, before any
     database writes occur.
"""

import functools
import hashlib
import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status

logger = logging.getLogger(__name__)


def _safe_log(value: str) -> str:
    """Strip CR/LF to prevent log injection attacks."""
    return str(value).replace("\r", "").replace("\n", " ")


# ─── 1. HTTP MIDDLEWARE ───────────────────────────────────────────────────────


class IdempotencyMiddleware:
    """
    Network-edge idempotency for all mutating HTTP requests.

    Flow:
        a) No key → pass through (non-idempotent safe mode).
        b) Key seen + cached response → replay immediately.
        c) Key seen + IN_FLIGHT → 409 (caller should back off).
        d) Key new → mark IN_FLIGHT, execute, cache 2xx response for 24h,
           clear lock on error so caller can legitimately retry.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ("POST", "PUT", "PATCH"):
            return self.get_response(request)

        idem_key = request.headers.get("X-Idempotency-Key")
        if not idem_key:
            return self.get_response(request)

        user_id = request.user.id if request.user.is_authenticated else "anon"
        cache_key = f"idem:api:{user_id}:{idem_key}"

        try:
            # Atomic lock (SETNX) — only the first request succeeds.
            # IN_FLIGHT state prevents concurrent duplicates.
            if not cache.add(cache_key, "IN_FLIGHT", timeout=60):
                cached = cache.get(cache_key)
                if cached == "IN_FLIGHT":
                    logger.warning(
                        f"[Idempotency] IN_FLIGHT duplicate: user={_safe_log(user_id)} key={_safe_log(idem_key)}"
                    )
                    return JsonResponse(
                        {"error": "Request already in progress. Retry after a moment."},
                        status=status.HTTP_409_CONFLICT,
                    )
                logger.info(
                    f"[Idempotency] Replaying cached response: user={_safe_log(user_id)} key={_safe_log(idem_key)}"
                )
                return JsonResponse(cached["data"], status=cached["status"])

        except Exception:
            logger.critical("[Idempotency] Redis failure (pre)")
            # Fail open — process the request without idempotency guarantees
            # rather than blocking all mutations during a Redis outage.
            return self.get_response(request)

        response = self.get_response(request)

        try:
            if 200 <= response.status_code < 300:
                try:
                    data = json.loads(response.content)
                except Exception:
                    data = {}
                cache.set(
                    cache_key,
                    {"status": response.status_code, "data": data},
                    timeout=86400,
                )
            else:
                # Do NOT cache error responses — allow the client to fix and retry.
                cache.delete(cache_key)
        except Exception:
            logger.critical("[Idempotency] Redis failure (post)")

        return response


# ─── 2. CELERY TASK DECORATOR ─────────────────────────────────────────────────


def idempotent_task(ttl=3600):
    """
    Ensures a Celery task body executes at most once per unique argument set
    within `ttl` seconds.

    The key is derived from (task_name, args, kwargs) via MD5.
    A two-phase Redis flag prevents both concurrent double-execution (race)
    and replay within the TTL window (retry storm):

        Phase 1 — RUNNING lock (60 s): blocks concurrent identical tasks.
        Phase 2 — DONE marker (ttl): blocks retried/replayed identical tasks.

    Usage:
        @shared_task(bind=True)
        @idempotent_task(ttl=3600)
        def settle_driver_payout(self, ride_id, payment_id):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build a stable, collision-resistant cache key
            func_name = getattr(func, "__qualname__", str(func))
            fingerprint = hashlib.sha256(
                f"{func_name}:{args!r}:{sorted(kwargs.items())!r}".encode()
            ).hexdigest()
            done_key = f"idem:task:done:{fingerprint}"
            running_key = f"idem:task:run:{fingerprint}"

            # Phase 1: reject concurrent duplicates
            if not cache.add(running_key, "1", timeout=120):
                logger.warning(
                    f"[Idempotency] Task already running: {_safe_log(func_name)}"
                )
                return None

            try:
                # Phase 2: reject already-completed tasks in TTL window
                if cache.get(done_key):
                    logger.info(
                        f"[Idempotency] Task already done (replay blocked): {_safe_log(func_name)}"
                    )
                    return None

                result = func(*args, **kwargs)
                cache.set(done_key, "1", timeout=ttl)
                return result
            finally:
                cache.delete(running_key)

        return wrapper

    return decorator


# ─── 3. WEBHOOK VIEW DECORATOR ──────────────────────────────────────────────


def idempotent_webhook(provider="razorpay"):
    """
    Deduplicates incoming webhook events using the provider's native event ID.

    Razorpay guarantees each webhook event has a unique X-Razorpay-Event-Id
    header.  If we've already processed this event_id we return 200 immediately
    (telling Razorpay not to retry) without executing any side-effects.

    The cache entry is set AFTER the handler succeeds to avoid suppressing
    legitimate retries on transient failures.

    Usage:
        @csrf_exempt
        @idempotent_webhook("razorpay")
        def payout_webhook(request):
            ...
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Extract event ID from provider header
            if provider == "razorpay":
                event_id = request.headers.get("X-Razorpay-Event-Id")
            else:
                event_id = None

            if not event_id:
                # No event ID — process normally (for providers that don't support it)
                return view_func(request, *args, **kwargs)

            cache_key = f"idem:webhook:{provider}:{event_id}"
            lock_key = f"idem:webhook:lock:{provider}:{event_id}"

            # Already processed?
            if cache.get(cache_key):
                logger.info(
                    f"[Idempotency] Duplicate webhook dropped: {_safe_log(provider)}/{_safe_log(event_id)}"
                )
                return JsonResponse({"status": "already_processed"}, status=200)

            # Concurrent duplicate?
            if not cache.add(lock_key, "1", timeout=60):
                logger.warning(
                    f"[Idempotency] Concurrent webhook: {_safe_log(provider)}/{_safe_log(event_id)}"
                )
                return JsonResponse({"error": "Concurrent processing"}, status=429)

            try:
                response = view_func(request, *args, **kwargs)
                # Only mark as processed on success — allow retries on failure
                if response.status_code < 400:
                    cache.set(cache_key, "1", timeout=86400)
                return response
            finally:
                cache.delete(lock_key)

        return wrapper

    return decorator


def _process_cached_response(cache_key, idem_key, user_id):
    cached = cache.get(cache_key)
    if cached == "IN_FLIGHT":
        logger.warning(
            f"[Idempotency] IN_FLIGHT duplicate: user={_safe_log(user_id)} key={_safe_log(idem_key)}"
        )
        return JsonResponse(
            {"error": "Request already in progress. Please wait."},
            status=status.HTTP_409_CONFLICT,
        )
    logger.info(
        f"[Idempotency] REPLAY cached response: user={_safe_log(user_id)} key={_safe_log(idem_key)}"
    )
    return JsonResponse(cached["data"], status=cached["status"])


def _cache_successful_response(response, cache_key, ttl):
    if 200 <= response.status_code < 300:
        if hasattr(response, "data"):
            response_data = response.data
        else:
            try:
                response_data = json.loads(response.content)
            except Exception:
                response_data = {}
        cache.set(
            cache_key,
            {"status": response.status_code, "data": response_data},
            timeout=ttl,
        )
    else:
        cache.delete(cache_key)


def idempotent_request(ttl=3600):
    """
    Decorator version of the Idempotency System for targeting specific views.
    Protects against duplicate POST/PUT/PATCH with X-Idempotency-Key.
    Replays 2xx responses cached for `ttl` duration.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if request.method not in ("POST", "PUT", "PATCH"):
                return view_func(self, request, *args, **kwargs)

            idem_key = request.headers.get("X-Idempotency-Key")
            if not idem_key:
                return view_func(self, request, *args, **kwargs)

            user_id = request.user.id if request.user.is_authenticated else "anon"
            cache_key = f"idem:api:{user_id}:{idem_key}"

            try:
                if not cache.add(cache_key, "IN_FLIGHT", timeout=60):
                    return _process_cached_response(cache_key, idem_key, user_id)
            except Exception:
                logger.exception("[Idempotency] Pre-exec cache error")
                return view_func(self, request, *args, **kwargs)

            response = view_func(self, request, *args, **kwargs)

            try:
                _cache_successful_response(response, cache_key, ttl)
            except Exception:
                logger.exception("[Idempotency] Post-exec cache error")

            return response

        return wrapper

    return decorator
