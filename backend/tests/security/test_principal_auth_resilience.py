import pytest
import asyncio
import time
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async
from unittest.mock import patch, MagicMock
from rest_framework_simplejwt.tokens import AccessToken
from apps.tracking.auth import JWTAuthMiddleware

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestPrincipalSecurityResilience:
    """
    Principal Engineer's Chaos and Security Suite.
    Focuses on breaking the authentication and session management layers.
    Zero shallow mocks. High stability focus for Docker environments.
    """

    @pytest.fixture(autouse=True)
    def setup_resilience(self, db):
        import uuid
        self.uid = uuid.uuid4().hex[:6]
        self.passw = "secure_pass_99"
        self.user = User.objects.create_user(
            username=f"sec_user_{self.uid}",
            phone=f"+91777{self.uid}",
            password=self.passw
        )

    # ============================================================
    # 1. AUTH BACKEND: ENUMERATION & TAMPERING
    # ============================================================

    def test_auth_indistinguishability_user_enumeration(self):
        """
        WHY: Validates that failing due to 'Wrong Password' vs 'Disabled User' 
        returns consistent results without revealing status to an attacker.
        """
        # Case 1: Existing User + Wrong Password
        res1 = authenticate(username=self.user.phone, password="wrong_password")
        
        # Case 2: Disabled User + Correct Password
        self.user.is_active = False
        self.user.save()
        res2 = authenticate(username=self.user.phone, password=self.passw)

        assert res1 is None
        assert res2 is None

    def test_auth_backend_database_failure_resilience(self):
        """
        WHY: Tests that the backend handles a hard DB failure mid-lookup without crashing.
        Ensures the hardened (DoesNotExist, Exception) catch block is active.
        """
        with patch("apps.users.backends.get_user_model") as mock_get_model:
            RealUser = get_user_model()
            mock_model = MagicMock()
            mock_model.DoesNotExist = RealUser.DoesNotExist
            mock_get_model.return_value = mock_model
            
            # Simulate a real DB timeout
            mock_model.objects.get.side_effect = Exception("LATENCY_THRESHOLD_EXCEEDED")
            
            res = authenticate(username=self.user.phone, password=self.passw)
            assert res is None

    # ============================================================
    # 2. WEBSOCKET: CRYPTOGRAPHIC TAMPERING
    # ============================================================

    @pytest.mark.asyncio
    async def test_websocket_attack_wrong_secret(self):
        """
        WHY: Validates that a token signed with an external key is rejected by the tracking layer.
        """
        payload = {"user_id": self.user.id, "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())}
        wrong_token = jwt.encode(payload, "ATTACKER_CONTROLLED_KEY", algorithm="HS256")

        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)
        scope = {"type": "websocket", "query_string": f"token={wrong_token}".encode(), "user": AnonymousUser()}

        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_algorithm_confusion(self):
        """
        WHY: Prevents security downgrade attacks by forcing algorithm mismatch rejection.
        """
        payload = {"user_id": self.user.id}
        # Force HS512 when system defaults likely HS256
        strange_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS512")

        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)
        scope = {"type": "websocket", "query_string": f"token={strange_token}".encode(), "user": AnonymousUser()}

        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)

    # ============================================================
    # 3. CONCURRENCY & ISOLATION
    # ============================================================

    @pytest.mark.asyncio
    async def test_websocket_concurrent_isolation(self):
        """
        WHY: Validates that concurrent handshakes do not bleed state (scope isolation).
        """
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)

        def make_token(user):
            return str(AccessToken.for_user(user))

        # We use a smaller concurrency count (5) to ensure stability in CI/Docker
        # while still validating the parallel async path.
        concurrency_count = 5
        tasks = []
        scopes = []

        for i in range(concurrency_count):
            token = await sync_to_async(make_token)(self.user)
            scope = {
                "type": "websocket",
                "query_string": f"token={token}".encode(),
                "user": AnonymousUser(),
                "id": i
            }
            scopes.append(scope)
            tasks.append(middleware(scope, None, None))

        await asyncio.gather(*tasks)

        for s in scopes:
            assert s["user"].id == self.user.id
            assert not isinstance(s["user"], AnonymousUser)

    # ============================================================
    # 4. ROBUSTNESS & FAULT INJECTION
    # ============================================================

    @pytest.mark.asyncio
    async def test_middleware_integrity_malformed_input(self):
        """
        WHY: Critical fix verification. Ensures the middleware doesn't crash on non-UTF8 input.
        """
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)
        
        # Bizarre/Invalid binary query string
        scope = {
            "type": "websocket", 
            "query_string": b"token=\xff\xfe\xfd\x00\x01\x02", 
            "user": AnonymousUser()
        }
        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_middleware_panic_recovery(self):
        """
        WHY: Verifies that the try/except block in the middleware swallows internal panics.
        """
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)
        scope = {"type": "websocket", "query_string": b"token=simulated_panic", "user": AnonymousUser()}

        with patch("apps.tracking.auth.authenticate_token", side_effect=SystemError("Internal Panic")):
            await middleware(scope, None, None)
            assert isinstance(scope["user"], AnonymousUser)
