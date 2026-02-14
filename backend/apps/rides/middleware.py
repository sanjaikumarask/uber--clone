from urllib.parse import parse_qs

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        token = None

        # 1️⃣ Try query string (?token=...)
        query_string = scope.get("query_string", b"").decode()
        if query_string:
            qs = parse_qs(query_string)
            token = qs.get("token", [None])[0]

        # 2️⃣ Fallback: Authorization header
        if not token:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization")
            if auth_header:
                try:
                    name, value = auth_header.decode().split()
                    if name.lower() == "bearer":
                        token = value
                except ValueError:
                    pass

        if token:
            user = await self.get_user(token)
            if user:
                scope["user"] = user

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token):
        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated_token)
        except (InvalidToken, TokenError):
            return None
