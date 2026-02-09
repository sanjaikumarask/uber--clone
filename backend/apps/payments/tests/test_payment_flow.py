from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

from apps.users.models import User
from apps.rides.models import Ride
from apps.payments.models import Payment


class TestPaymentFlow(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="rider",
            password="pass1234",
            role=User.ROLE_RIDER,
        )

        self.ride = Ride.objects.create(
            rider=self.user,
            pickup_lat=1,
            pickup_lng=1,
            drop_lat=2,
            drop_lng=2,
            status=Ride.Status.COMPLETED,
            final_fare=150,
        )

        self.client.force_authenticate(self.user)

    @patch("apps.payments.razorpay_client.razorpay_client.order.create")
    def test_create_payment(self, mock_create):
        mock_create.return_value = {
            "id": "order_123",
            "amount": 15000,
            "currency": "INR",
        }

        res = self.client.post(f"/api/payments/create/{self.ride.id}/")

        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            Payment.objects.filter(ride_id=self.ride.id).exists()
        )
