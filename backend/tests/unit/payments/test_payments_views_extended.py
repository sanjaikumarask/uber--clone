import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from apps.users.models import User
from apps.rides.models import Ride
from apps.payments.models import Payment, LedgerEntry

@pytest.fixture
def rider_user():
    return User.objects.create_user(username="rider_pay", phone="+919999999999")

@pytest.fixture
def driver_user():
    user = User.objects.create_user(username="driver_pay", phone="+918888888888", role="driver")
    # Driver profile created by signal
    return user

@pytest.fixture
def auth_client(api_client, rider_user):
    api_client.force_authenticate(user=rider_user)
    return api_client

@pytest.mark.django_db
class TestPaymentViewsExtended:

    def test_simulated_payment_success(self, auth_client, rider_user, driver_user):
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.COMPLETED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100,
            final_fare=150
        )
        
        url = f"/api/payments/simulate/{ride.id}/"
        response = auth_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        
        ride.refresh_from_db()
        assert Payment.objects.filter(ride_id=ride.id, status="CAPTURED").exists()

    @patch('apps.payments.views.razorpay_client')
    def test_create_payment_order(self, mock_razorpay, auth_client, rider_user, driver_user):
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.COMPLETED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100,
            final_fare=150
        )
        
        # Mock Razorpay order creation
        mock_order = MagicMock()
        mock_order.create.return_value = {
            "id": "order_123",
            "amount": 15000,
            "currency": "INR"
        }
        mock_razorpay.order = mock_order
        mock_razorpay.auth = ["key_id", "secret"]
        
        url = f"/api/payments/create/{ride.id}/"

        response = auth_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["order_id"] == "order_123"
        
        payment = Payment.objects.get(ride_id=ride.id)
        assert payment.gateway_order_id == "order_123"

    @patch('apps.payments.views.razorpay_client')
    def test_verify_payment_success(self, mock_razorpay, auth_client, rider_user, driver_user):
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.COMPLETED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100,
            final_fare=150
        )
        payment = Payment.objects.create(
            user=rider_user,
            ride_id=ride.id,
            amount=150,
            status="CREATED",
            gateway_order_id="order_456"
        )
        
        # Mock signature verification (raises nothing on success)
        mock_razorpay.utility.verify_payment_signature.return_value = True
        
        url = "/api/payments/verify/"
        payload = {
            "razorpay_order_id": "order_456",
            "razorpay_payment_id": "pay_789",
            "razorpay_signature": "sig_000"
        }
        response = auth_client.post(url, payload)
        
        assert response.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == "CAPTURED"
        assert payment.gateway_payment_id == "pay_789"
