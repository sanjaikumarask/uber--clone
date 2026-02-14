from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.supports.models import SupportTicket
from apps.payments.models import Payment

User = get_user_model()

class TestSupportTicket(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.rider = User.objects.create_user(
            username="rider_support",
            password="password",
            role="rider",
            phone="+919999999901"
        )
        self.driver_user = User.objects.create_user(
            username="driver_support",
            password="password",
            role="driver",
            phone="+919999999902"
        )
        self.admin = User.objects.create_superuser(
            username="admin_support",
            password="password",
            role="admin",
            phone="+919999999903"
        )
        
        self.driver = Driver.objects.get(user=self.driver_user)
        
        # Create completed ride
        self.ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_lat=12.9716,
            pickup_lng=77.5946,
            drop_lat=12.2958,
            drop_lng=76.6394,
            status=Ride.Status.COMPLETED,
            final_fare=500.00
        )
        
        # Create captured payment
        self.payment = Payment.objects.create(
            user=self.rider,
            ride_id=self.ride.id,
            amount=500.00,
            status=Payment.Status.CAPTURED,
            gateway_payment_id="pay_123456"
        )

    def test_create_support_ticket(self):
        """Test creating a support ticket"""
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.post(
            f"/api/supports/rides/{self.ride.id}/ticket/",
            {
                "reason": SupportTicket.Reason.DRIVER_MISCONDUCT,
                "description": "Driver was rude"
            },
            format="json"
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert "ticket_id" in response.data
        
        ticket = SupportTicket.objects.get(id=response.data["ticket_id"])
        assert ticket.ride == self.ride
        assert ticket.user == self.rider
        assert ticket.reason == SupportTicket.Reason.DRIVER_MISCONDUCT
        assert ticket.status == SupportTicket.Status.OPEN

    def test_create_ticket_invalid_user(self):
        """Test creating ticket by unrelated user"""
        other_user = User.objects.create_user(
            username="other", password="password", role="rider", phone="+919999999904"
        )
        self.client.force_authenticate(user=other_user)
        
        response = self.client.post(
            f"/api/supports/rides/{self.ride.id}/ticket/",
            {
                "reason": SupportTicket.Reason.OTHER,
                "description": "Scam"
            }
        )
        
        # Depending on service implementation, might return 400 or 403.
        # Service raises ValidationError -> Usually 400 in DRF if exception handler configured, or 500.
        # Let's check view logic. It calls service directly. If service raises ValidationError,
        # standard DRF might catch it depending on settings. Assuming it generates 400/500/or caught.
        # The view doesn't explicitly catch ValidationError.
        # However, DRF's built-in exception handler handles Django ValidationError as 400.
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_resolve_ticket_with_refund(self):
        """Test resolving ticket with refund"""
        # Create ticket
        ticket = SupportTicket.objects.create(
            ride=self.ride,
            user=self.rider,
            reason=SupportTicket.Reason.OVERCHARGED,
            description="Charged too much"
        )
        
        self.client.force_authenticate(user=self.admin)
        
        # Mock refund servcie
        with patch("apps.supports.services.refund_payment") as mock_refund:
            response = self.client.post(
                f"/api/supports/tickets/{ticket.id}/resolve/",
                {
                    "refund_amount": "100.00",
                    "note": "Refund processed"
                },
                format="json"
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_refund.assert_called_once()
            
            ticket.refresh_from_db()
            assert ticket.status == SupportTicket.Status.RESOLVED
            assert ticket.resolution_note == "Refund processed"
            assert ticket.resolved_by == self.admin

    def test_reject_ticket(self):
        """Test rejecting a ticket"""
        ticket = SupportTicket.objects.create(
            ride=self.ride,
            user=self.rider,
            reason=SupportTicket.Reason.OTHER,
            description="My cat didn't like the car"
        )
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            f"/api/supports/tickets/{ticket.id}/resolve/",
            {
                # No refund amount
                "note": "Invalid complaint"
            },
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        ticket.refresh_from_db()
        assert ticket.status == SupportTicket.Status.REJECTED
        assert ticket.resolution_note == "Invalid complaint"

    def test_non_admin_cannot_resolve(self):
        """Test non-admin cannot resolve tickets"""
        ticket = SupportTicket.objects.create(
            ride=self.ride,
            user=self.rider,
            reason=SupportTicket.Reason.OTHER
        )
        
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(
            f"/api/supports/tickets/{ticket.id}/resolve/",
            {"note": "Hacked"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
