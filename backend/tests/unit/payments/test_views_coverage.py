import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
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
def other_rider(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"other_{uid}", role="rider")

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
    return Ride.objects.create(
        rider=rider, driver=driver_profile, status=Ride.Status.COMPLETED,
        pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1,
        final_fare=Decimal("150.00")
    )

@pytest.mark.django_db
class TestPaymentsViewsCoverage:

    # ----------------------------------------------------
    # SimulatedPaymentView
    # ----------------------------------------------------
    def test_simulated_payment_ride_not_found(self, api_client, rider):
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/simulate/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_simulated_payment_wrong_rider(self, api_client, other_rider, ride):
        api_client.force_authenticate(user=other_rider)
        response = api_client.post(f'/api/payments/simulate/{ride.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_simulated_payment_wrong_status(self, api_client, rider, ride):
        ride.status = Ride.Status.ONGOING
        ride.save()
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/simulate/{ride.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_simulated_payment_already_paid(self, api_client, rider, ride):
        Payment.objects.create(user=rider, ride_id=ride.id, amount=Decimal("150.00"), status=Payment.Status.CAPTURED)
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/simulate/{ride.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "already_paid"

    def test_simulated_payment_reuse_created(self, api_client, rider, ride):
        p = Payment.objects.create(user=rider, ride_id=ride.id, amount=Decimal("150.00"), status=Payment.Status.CREATED)
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/simulate/{ride.id}/')
        assert response.status_code == status.HTTP_200_OK
        p.refresh_from_db()
        assert p.status == Payment.Status.CAPTURED
        assert p.gateway == "simulation"

    # ----------------------------------------------------
    # CreatePaymentOrderView
    # ----------------------------------------------------
    def test_create_order_ride_not_found(self, api_client, rider):
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_order_wrong_rider(self, api_client, other_rider, ride):
        api_client.force_authenticate(user=other_rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_order_wrong_status(self, api_client, rider, ride):
        ride.status = Ride.Status.ONGOING
        ride.save()
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_order_invalid_fare(self, api_client, rider, ride):
        ride.final_fare = Decimal("-10.00")
        ride.save()
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.payments.views.razorpay_client', None)
    def test_create_order_no_gateway(self, api_client, rider, ride):
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch('apps.payments.views.razorpay_client')
    def test_create_order_already_captured(self, mock_razorpay, api_client, rider, ride):
        Payment.objects.create(user=rider, ride_id=ride.id, amount=Decimal("150.00"), status=Payment.Status.CAPTURED)
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already been captured" in response.data["error"]

    @patch('apps.payments.views.razorpay_client')
    def test_create_order_razorpay_success_creates_payment(self, mock_razorpay, api_client, rider, ride):
        mock_razorpay.order.create.return_value = {"id": "order_123", "amount": 15000, "currency": "INR"}
        mock_razorpay.auth = ("key", "sec")
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_200_OK
        p = Payment.objects.filter(ride_id=ride.id).first()
        assert p is not None

    @patch('apps.payments.views.razorpay_client')
    def test_create_order_razorpay_error(self, mock_razorpay, api_client, rider, ride):
        mock_razorpay.order.create.side_effect = Exception("Authentication failed")
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/create/{ride.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ----------------------------------------------------
    # VerifyPaymentView
    # ----------------------------------------------------
    @patch('apps.payments.views.razorpay_client', None)
    def test_verify_no_gateway(self, api_client, rider):
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/verify/', {})
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch('apps.payments.views.razorpay_client')
    def test_verify_missing_payload(self, mock_razorpay, api_client, rider):
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/verify/', {"razorpay_order_id": "abc"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.payments.views.razorpay_client')
    def test_verify_invalid_signature(self, mock_razorpay, api_client, rider):
        mock_razorpay.utility.verify_payment_signature.side_effect = Exception("Bad Sig")
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/verify/', {
            "razorpay_order_id": "1", "razorpay_payment_id": "2", "razorpay_signature": "3"
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.payments.views.razorpay_client')
    def test_verify_payment_not_found(self, mock_razorpay, api_client, rider):
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/verify/', {
            "razorpay_order_id": "missing_order", "razorpay_payment_id": "2", "razorpay_signature": "3"
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch('apps.payments.views.razorpay_client')
    def test_verify_wrong_user(self, mock_razorpay, api_client, other_rider, rider, ride):
        Payment.objects.create(user=rider, ride_id=ride.id, amount=Decimal("150.00"), status=Payment.Status.CREATED, gateway_order_id="order_123")
        api_client.force_authenticate(user=other_rider)
        response = api_client.post(f'/api/payments/verify/', {
            "razorpay_order_id": "order_123", "razorpay_payment_id": "2", "razorpay_signature": "3"
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('apps.payments.views.razorpay_client')
    def test_verify_already_captured(self, mock_razorpay, api_client, rider, ride):
        Payment.objects.create(user=rider, ride_id=ride.id, amount=Decimal("150.00"), status=Payment.Status.CAPTURED, gateway_order_id="order_123")
        api_client.force_authenticate(user=rider)
        response = api_client.post(f'/api/payments/verify/', {
            "razorpay_order_id": "order_123", "razorpay_payment_id": "2", "razorpay_signature": "3"
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "already_captured"

