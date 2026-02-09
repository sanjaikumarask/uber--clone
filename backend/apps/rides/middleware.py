import logging
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.db import close_old_connections
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        logger.info("WS middleware entered")

        try:
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)
            token_list = query_params.get("token")

            if not token_list:
                logger.warning("WS no token")
                scope["user"] = AnonymousUser()
                return await self.inner(scope, receive, send)

            token = token_list[0]
            validated = JWTAuthentication().get_validated_token(token)

            user = await self.get_user(validated)
            scope["user"] = user

            logger.info("WS authenticated user=%s", user.id)

        except InvalidToken:
            logger.exception("WS invalid token")
            scope["user"] = AnonymousUser()

        except Exception:
            logger.exception("WS middleware crash")
            raise  # IMPORTANT: surface the error

        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def get_user(self, validated_token):
        return JWTAuthentication().get_user(validated_token)
