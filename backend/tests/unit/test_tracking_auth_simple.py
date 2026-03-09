import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import AnonymousUser
from apps.tracking.auth import JWTAuthMiddleware

async def dummy_app(scope, receive, send):
    return "done"

@pytest.mark.asyncio
async def test_jwt_auth_middleware_no_token():
    middleware = JWTAuthMiddleware(dummy_app)
    scope = {"query_string": b""}
    
    await middleware(scope, None, None)
    assert isinstance(scope["user"], AnonymousUser)

@pytest.mark.asyncio
async def test_jwt_auth_middleware_with_token():
    middleware = JWTAuthMiddleware(dummy_app)
    scope = {"query_string": b"token=valid"}
    
    with patch("apps.tracking.auth.authenticate_token") as mock_auth:
        user = MagicMock()
        mock_auth.return_value = user
        await middleware(scope, None, None)
        assert scope["user"] == user
        mock_auth.assert_called_with("valid")
