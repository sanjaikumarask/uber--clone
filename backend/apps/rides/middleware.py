from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        token = self._get_token_from_scope(scope)

        if token:
            user = await self.get_user(token)
            if user:
                if self._check_rate_limit(user.id):
                    return None  # Drop connection
                scope["user"] = user

        return await super().__call__(scope, receive, send)

    def _get_token_from_scope(self, scope):
        # 1. Try query string (?token=...)
        query_string = scope.get("query_string", b"").decode()
        if query_string:
            qs = parse_qs(query_string)
            token = qs.get("token", [None])[0]
            if token:
                return token

        # 2. Fallback: Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")
        if auth_header:
            try:
                name, value = auth_header.decode().split()
                if name.lower() == "bearer":
                    return value
            except ValueError:
                pass
        return None

    def _check_rate_limit(self, user_id):
        # Reject > 15 socket connects per minute from same user
        from django.core.cache import cache

        cache_key = f"ws_ratelimit_{user_id}"
        attempts = cache.get(cache_key, 0)
        if attempts > 15:
            return True
        cache.set(cache_key, attempts + 1, timeout=60)
        return False

    @database_sync_to_async
    def get_user(self, token):
        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated_token)
        except (InvalidToken, TokenError):
            return None
