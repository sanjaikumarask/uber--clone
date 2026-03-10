import pytest

from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from decimal import Decimal
import uuid

from apps.rides.models import Ride
from apps.payments.models import Payment, LedgerEntry

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def rider(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"rider_{uid}", role="rider")

@pytest.fixture
def driver_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"driver_{uid}", role="driver")

@pytest.fixture
def ride(rider, driver_user):
    from apps.drivers.models import Driver
    driver_profile, _ = Driver.objects.get_or_create(
        user=driver_user, defaults={'status': Driver.Status.ONLINE, 'level': Driver.Level.NORMAL, 'is_verified': True}
    )
    driver_profile.status = Driver.Status.ONLINE
    driver_profile.is_verified = True
    driver_profile.save()
    return Ride.objects.create(
        rider=rider, driver=driver_profile, status=Ride.Status.COMPLETED,
        pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1,
        final_fare=Decimal("150.00")
    )

@pytest.mark.django_db
class TestPaymentsViewsWebCoverage:

    def test_web_checkout_unauthenticated(self, api_client, ride):
        response = api_client.get(f'/api/payments/checkout/{ride.id}/')
        # DRF generic view will return 401/403 if it uses rest_framework permissions, but it seems there is none defined directly in the file except inherited.
        # Actually CreatePaymentOrderView has permissions = [IsAuthenticated] usually.
        assert response.status_code in [401, 403]

    @patch('apps.payments.views_web.razorpay_client', None)
    def test_web_checkout_no_gateway(self, api_client, rider, ride):
        api_client.force_authenticate(user=rider)
        response = api_client.get(f'/api/payments/checkout/{ride.id}/')
        assert response.status_code == 302
        assert "GatewayConfigMissing" in response.url

    @patch('apps.payments.views_web.razorpay_client')
    def test_web_checkout_success(self, mock_razorpay, api_client, rider, ride):
        mock_razorpay.auth = ("key_test", "secret_test")
        mock_razorpay.order.create.return_value = {"id": "order_web_123"}
        
        api_client.force_authenticate(user=rider)
        
        # We need the templates for rendering. We can mock render if TemplateDoesNotExist
        with patch('apps.payments.views_web.render') as mock_render:
            from django.http import HttpResponse
            mock_render.return_value = HttpResponse(b"<html>Checkout</html>")
            response = api_client.get(f'/api/payments/checkout/{ride.id}/')
            
            assert response.status_code == 200
            assert response.content == b"<html>Checkout</html>"
            
            # Verify Payment is created
            payment = Payment.objects.filter(ride_id=ride.id).first()
            assert payment is not None
            assert payment.gateway_order_id == "order_web_123"

    @patch('apps.payments.views_web.razorpay_client')
    def test_web_verify_success(self, mock_razorpay, api_client, rider, ride):
        payment = Payment.objects.create(
            user=rider, ride_id=ride.id, amount=Decimal("150.00"), status=Payment.Status.CREATED,
            gateway_order_id="order_web_123"
        )
        data = {
            "razorpay_order_id": "order_web_123",
            "razorpay_payment_id": "pay_web_123",
            "razorpay_signature": "sig_valid"
        }
        
        # mock_razorpay.utility.verify_payment_signature does not raise == valid
        response = api_client.post('/api/payments/verify-web/', data)
        assert response.status_code == 302
        assert "success-page" in response.url
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.CAPTURED
        
        # Idempotent re-verify
        response2 = api_client.post('/api/payments/verify-web/', data)
        assert response2.status_code == 302

    @patch('apps.payments.views_web.razorpay_client')
    def test_web_verify_failure(self, mock_razorpay, api_client):
        mock_razorpay.utility.verify_payment_signature.side_effect = Exception("Invalid signature")
        
        data = {
            "razorpay_order_id": "order_web_invalid",
            "razorpay_payment_id": "pay_web_invalid",
            "razorpay_signature": "sig_invalid"
        }
        
        response = api_client.post('/api/payments/verify-web/', data)
        assert response.status_code == 302
        assert "error" in response.url
