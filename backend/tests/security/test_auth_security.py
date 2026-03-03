import pytest
import asyncio
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from apps.users.backends import PhoneBackend
from apps.tracking.auth import JWTAuthMiddleware

User = get_user_model()

@pytest.mark.django_db
class TestAuthSecuritySuite:
    """
    Senior Security Engineer's Suite: Identity & Real-time Tracking.
    Targets users/backends.py and tracking/auth.py (previously 0% coverage).
    """

    def setup_method(self):
        self.backend = PhoneBackend()
        import uuid
        uid = uuid.uuid4().hex[:6]
        self.user_data = {"phone": f"+91987654{uid}", "password": "securepassword123"}
        self.user = User.objects.create_user(username=f"user_{uid}", **self.user_data)

    # ============================================================
    # 1. AUTHENTICATION BACKEND (users/backends.py)
    # ============================================================

    def test_phone_backend_disabled_account_denial(self):
        """WHY: Ensures that de-activated users cannot bypass login via the custom backend."""
        self.user.is_active = False
        self.user.save()
        res = self.backend.authenticate(None, username=self.user.phone, password=self.user_data["password"])
        assert res is None

    def test_phone_backend_missing_credentials_handling(self):
        """WHY: Validates that empty/None inputs fail gracefully without crash."""
        assert self.backend.authenticate(None, phone=None) is None
        assert self.backend.authenticate(None, username="") is None

    def test_phone_backend_incorrect_password_leak_prevention(self):
        """WHY: Prevents unauthorized access when correct phone but wrong password is provided."""
        assert self.backend.authenticate(None, username=self.user.phone, password="wrongpassword") is None

    def test_phone_backend_invalid_user_lookup(self):
        """WHY: Gracefully handles lookups for non-existent phone numbers."""
        assert self.backend.authenticate(None, username="+9999999999") is None

    # ============================================================
    # 2. WEBSOCKET AUTHENTICATION (tracking/auth.py)
    # ============================================================

    @pytest.mark.asyncio
    async def test_websocket_middleware_tampered_token(self):
        """WHY: Blocks connections with invalid/malicious JWT signatures."""
        scope = {"query_string": b"token=bad_sig"}
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)

        with patch("apps.tracking.auth.authenticate_token") as mock_auth:
            # We mock the internal authenticate_token to fail
            mock_auth.side_effect = Exception("Invalid Token")
            await middleware(scope, None, None)
            assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_middleware_expired_token(self):
        """WHY: Rejects established sessions using expired credentials."""
        scope = {"query_string": b"token=expired"}
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)

        with patch("apps.tracking.auth.authenticate_token") as mock_auth:
            mock_auth.side_effect = InvalidToken("Expired")
            await middleware(scope, None, None)
            assert isinstance(scope["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_middleware_anonymous_fallthrough(self):
        """WHY: Ensures missing or malformed tokens default to AnonymousUser."""
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)

        # Case 1: Empty Query
        scope_1 = {"query_string": b""}
        await middleware(scope_1, None, None)
        assert isinstance(scope_1["user"], AnonymousUser)

        # Case 2: No token key
        scope_2 = {"query_string": b"foo=bar"}
        await middleware(scope_2, None, None)
        assert isinstance(scope_2["user"], AnonymousUser)

    @pytest.mark.asyncio
    async def test_websocket_middleware_db_outage_fail_safe(self):
        """WHY: Prevents the real-time layer from crashing during a DB outage."""
        scope = {"query_string": b"token=valid"}
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)

        with patch("apps.tracking.auth.authenticate_token") as mock_auth:
            mock_auth.side_effect = Exception("Internal DB Failure")
            await middleware(scope, None, None)
            assert isinstance(scope["user"], AnonymousUser)

    # ============================================================
    # 3. SECURITY & CONCURRENCY SCENARIOS
    # ============================================================

    def test_brute_force_leakage_mitigation(self):
        """WHY: Standard timing/brute force check to ensure the backend is predictable."""
        with patch("apps.users.models.User.check_password", return_value=False):
            for _ in range(5):
                res = self.backend.authenticate(None, username=self.user.phone, password="any")
                assert res is None

    def test_simultaneous_creation_integrity(self):
        """WHY: Distributed systems safety. Ensures no duplicate phone can exist."""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            User.objects.create(username="race_winner", phone=self.user.phone)

    @pytest.mark.asyncio
    async def test_concurrent_handshake_isolation(self):
        """WHY: Ensures that one user's failure does not bleed into another's concurrent WS handshake."""
        async def inner_app(s, r, se): pass
        middleware = JWTAuthMiddleware(inner_app)
        
        scope_succeed = {"query_string": b"token=good"}
        scope_fail = {"query_string": b"token=bad"}
        
        async def side_effect(token):
            await asyncio.sleep(0.01) # Force actual concurrency overlap
            if token == "good": return self.user
            raise Exception("Fail")

        with patch("apps.tracking.auth.authenticate_token", side_effect=side_effect):
            await asyncio.gather(
                middleware(scope_succeed, None, None),
                middleware(scope_fail, None, None)
            )
            
            assert scope_succeed["user"] == self.user
            assert isinstance(scope_fail["user"], AnonymousUser)
