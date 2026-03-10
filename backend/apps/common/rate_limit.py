# apps/common/rate_limit.py
import logging

from django.http import JsonResponse

from apps.common.backpressure import endpoint_cooldown

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Global Redis-based Rate Limiting Middleware.

    Protects sensitive, write/mutating endpoints from brute-force and abuse.
    Read-only polling endpoints (e.g. nearby-drivers) are intentionally excluded —
    they are already protected by JWT authentication.

    Key design note:
        All requests from mobile apps behind Nginx arrive with the same
        Docker internal IP (172.18.0.x). Keying the rate limit on IP would
        share the bucket across ALL users. We MUST use the JWT user_id claim
        as the rate-limit key. Unauthenticated requests fall back to X-Forwarded-For.
    """

    # Exact path -> (max_calls, window_seconds)
    # Only include WRITE / MUTATION endpoints that need abuse protection.
    # DO NOT add polling/read endpoints here.
    SENSITIVE_ENDPOINTS = {
        "/api/users/login/": (5, 60),  # 5 login attempts per minute
        "/api/rides/request/": (5, 60),  # 5 ride creations per minute
        "/api/rides/": (5, 60),  # same — POST /api/rides/ alias
        "/api/rides/verify-otp/": (10, 60),  # 10 OTP attempts per minute
        "/api/payments/": (10, 60),  # 10 payment calls per minute
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_rate_limit_key(self, request) -> str:
        """
        Returns a per-user or per-IP key for the rate limiter.

        Priority:
        1. JWT user_id (most precise — works even behind a shared Nginx IP)
        2. X-Forwarded-For real client IP (set by Nginx)
        3. REMOTE_ADDR fallback
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            try:
                from rest_framework_simplejwt.tokens import AccessToken

                token_str = auth_header.split(" ")[1]
                token = AccessToken(token_str)
                user_id = token.get("user_id")
                if user_id:
                    logger.info(f"[RateLimit] JWT Found: user_id={user_id}")
                    return f"user:{user_id}"
            except Exception as e:
                logger.warning(f"[RateLimit] JWT Decode Failed: {e}")

        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return f"ip:{xff.split(',')[0].strip()}"

        return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"

    def __call__(self, request):
        path = request.path

        # Exact-match lookup (faster, avoids prefix collision bugs)
        config = self.SENSITIVE_ENDPOINTS.get(path)

        if config:
            max_calls, window = config
            key = self._get_rate_limit_key(request)

            if not endpoint_cooldown(
                key, f"rl:{path}", max_calls=max_calls, window=window
            ):
                logger.warning(f"[RateLimit] 🛑 Blocked: key={key} path={path}")
                return JsonResponse(
                    {"error": "Too many requests. Please try again later."},
                    status=429,
                )

        return self.get_response(request)
