import pytest
import asyncio
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from apps.tracking.auth import JWTAuthMiddleware

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestAuthSystemExecution:
    """
    Django Testing Expert's Execution Suite.
    Forces execution through the full Django Auth and ASGI stack with zero function-level mocking.
    """

    @pytest.fixture
    def test_user(self, db):
        import uuid
        uid = uuid.uuid4().hex[:6]
        user = User.objects.create_user(
            username=f"real_user_{uid}",
            phone=f"+91888{uid}",
            password="real_password_123"
        )
        return user

    # ============================================================
    # 1. PHONE BACKEND EXECUTION (users/backends.py)
    # ============================================================

    def test_phone_backend_full_stack_execution(self, test_user):
        """
        WHY: Triggers the PhoneBackend via the standard Django authenticate() system.
        Ensures authenticate(), check_password(), and user_can_authenticate() are ALL executed.
        """
        # Scenario A: Success via Phone + Password
        user = authenticate(username=test_user.phone, password="real_password_123")
        assert user is not None
        assert user.pk == test_user.pk

        # Scenario B: Fail via Wrong Password (triggers check_password path)
        user_fail = authenticate(username=test_user.phone, password="wrong_password")
        assert user_fail is None

        # Scenario C: Fail via Inactive User (triggers user_can_authenticate path)
        test_user.is_active = False
        test_user.save()
        user_inactive = authenticate(username=test_user.phone, password="real_password_123")
        assert user_inactive is None

        # Scenario D: Fail via Non-Existent User (triggers DoesNotExist path)
        user_none = authenticate(username="+9999999999", password="any")
        assert user_none is None

        # Scenario E: Fail via Missing Phone (triggers phone is None path)
        user_missing = authenticate(username=None, password="any")
        assert user_missing is None

    # ============================================================
    # 2. WEBSOCKET MIDDLEWARE EXECUTION (tracking/auth.py)
    # ============================================================

    @pytest.mark.asyncio
    async def test_jwt_middleware_full_stack_execution(self, test_user):
        """
        WHY: Executes the JWTAuthMiddleware as a true ASGI application.
        Ensures execution through token validation and AnonymousUser fallbacks.
        """
        # Generate Access Token (avoids blacklisting/refresh logic)
        def get_real_token(user):
            return str(AccessToken.for_user(user))

        token = await sync_to_async(get_real_token)(test_user)

        # Mock ASGI app
        async def inner_app(scope, receive, send):
            pass

        middleware = JWTAuthMiddleware(inner_app)

        # Scenario A: Valid Token (Query String)
        scope_valid = {
            "type": "websocket",
            "query_string": f"token={token}".encode(),
            "user": AnonymousUser()
        }
        await middleware(scope_valid, None, None)
        
        # Verify user retrieval
        def verify_user(scope):
            return scope["user"].pk == test_user.pk and not isinstance(scope["user"], AnonymousUser)
        
        is_valid = await sync_to_async(verify_user)(scope_valid)
        assert is_valid

        # Scenario B: Invalid/Garbage Token (triggers Exception and AnonymousUser fallback)
        scope_invalid = {
            "type": "websocket",
            "query_string": b"token=garbage_not_a_jwt_at_all",
            "user": AnonymousUser()
        }
        await middleware(scope_invalid, None, None)
        assert isinstance(scope_invalid["user"], AnonymousUser)

        # Scenario C: Missing Token (triggers if not token path)
        scope_missing = {
            "type": "websocket",
            "query_string": b"foo=bar",
            "user": AnonymousUser()
        }
        await middleware(scope_missing, None, None)
        assert isinstance(scope_missing["user"], AnonymousUser)

    def test_phone_backend_get_user_execution(self, test_user):
        """
        WHY: Forces execution of the get_user() method in the PhoneBackend.
        """
        from apps.users.backends import PhoneBackend
        backend = PhoneBackend()
        
        # Valid User
        user = backend.get_user(test_user.id)
        assert user.id == test_user.id
        
        # Non-Existent User ID
        no_user = backend.get_user(999999)
        assert no_user is None
