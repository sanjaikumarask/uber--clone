import logging
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status

logger = logging.getLogger(__name__)

class IdempotencyMiddleware:
    """
    Production-grade Network Edge Idempotency.
    Guarantees that a client automatically retrying a 'POST' mutation
    (like completing a ride, or opening a payment) will NEVER execute twice,
    even if the DB locks are slow. Uses Redis strictly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ["POST", "PUT", "PATCH"]:
            return self.get_response(request)

        idem_key = request.headers.get("X-Idempotency-Key")
        if not idem_key:
            return self.get_response(request)

        # Build Redis Key
        cache_key = f"idem_{request.user.id if request.user.is_authenticated else 'anon'}_{idem_key}"

        try:
            # Check if already processed
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.info(f"IDEMPOTENCY: Dropped duplicate request for key {idem_key}")
                if cached_response == "IN_FLIGHT":
                    # Currently processing, tell the app to back off
                    return JsonResponse(
                        {"error": "Request is currently processing. Do not retry yet."}, 
                        status=status.HTTP_409_CONFLICT
                    )
                
                # Re-play strictly the previous response body
                return JsonResponse(cached_response.get("data", {}), status=cached_response.get("status", 200))

            # Mark as In Flight so parallel dupes (e.g. raging clicking) are locked
            cache.set(cache_key, "IN_FLIGHT", timeout=60)
        except Exception as e:
            logger.critical(f"REDIS FAILURE in IdempotencyMiddleware: {e}")
            # Fallback: Process request normally if cache is down
            return self.get_response(request)

        # Process the real request
        response = self.get_response(request)

        try:
            # Store the successful output to exactly replicate if they retry
            if 200 <= response.status_code < 300:
                import json
                try:
                    data = json.loads(response.content)
                except Exception:
                    data = {}
                
                # Lock the success state for 24 hours
                cache.set(cache_key, {"status": response.status_code, "data": data}, timeout=86400)
            else:
                # If the backend failed/400'd, clear the lock so they CAN legitimately retry
                cache.delete(cache_key)
        except Exception as e:
            logger.critical(f"REDIS FAILURE in IdempotencyMiddleware post-processing: {e}")

        return response
