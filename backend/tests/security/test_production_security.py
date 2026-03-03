import pytest
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from apps.tracking.auth import JWTAuthMiddleware
from rest_framework_simplejwt.tokens import AccessToken

@pytest.mark.django_db
class TestProductionSecurity:
    """
    Principal-level security audit:
    - Cryptographic verification (JWT)
    - Unauthorized escalation attempts
    - WebSocket handshake security
    """

    def test_jwt_tampering_rejection(self, api_client, user):
        """Verify that modifying the JWT payload without resigning fails."""
        token = AccessToken.for_user(user)
        token_str = str(token)
        
        # Split token
        header, payload, signature = token_str.split('.')
        
        # Tamper with payload (e.g. change user_id or roles)
        import base64
        import json
        payload_data = json.loads(base64.b64decode(payload + '==').decode())
        payload_data['user_id'] = 999 
        tampered_payload = base64.b64encode(json.dumps(payload_data).encode()).decode().rstrip('=')
        
        tampered_token = f"{header}.{tampered_payload}.{signature}"
        
        url = reverse("ride-list")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
        response = api_client.get(url)
        
        # DRF/SimpleJWT should reject due to signature mismatch
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_denial(self, api_client, user):
        """Verify that expired tokens are rejected immediately."""
        token = AccessToken.for_user(user)
        # Set expiry to past
        token.set_exp(lifetime=timedelta(seconds=-1))
        
        url = reverse("ride-list")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_websocket_middleware_unauthorized(self):
        """Verifies that WebSocket middleware correctly defaults to AnonymousUser on invalid token."""
        async def mock_app(scope, receive, send):
            assert isinstance(scope["user"], AnonymousUser)
            
        middleware = JWTAuthMiddleware(mock_app)
        
        # 1. No token
        scope = {"type": "websocket", "query_string": b"", "user": None}
        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)

        # 2. Garbage token
        scope = {"type": "websocket", "query_string": b"token=garbage_data_123", "user": None}
        await middleware(scope, None, None)
        assert isinstance(scope["user"], AnonymousUser)

    def test_cross_role_access_denial(self, driver_client):
        """Verify that a driver cannot access rider-only endpoints (Create Ride)."""
        url = reverse("ride-list") # POST here is rider-only
        payload = {"pickup_lat": 1.0, "pickup_lng": 1.0, "drop_lat": 2.0, "drop_lng": 2.0}
        
        response = driver_client.post(url, payload)
        
        # Assuming the view uses IsRider permission
        assert response.status_code == status.HTTP_403_FORBIDDEN
