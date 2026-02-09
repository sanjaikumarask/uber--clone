from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from channels.db import database_sync_to_async


@database_sync_to_async
def authenticate_token(token):
    jwt_auth = JWTAuthentication()
    validated = jwt_auth.get_validated_token(token)
    return jwt_auth.get_user(validated)


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope["query_string"].decode())
        token = query.get("token")

        if not token:
            scope["user"] = AnonymousUser()
            return await self.app(scope, receive, send)

        try:
            scope["user"] = await authenticate_token(token[0])
        except Exception:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
