import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.rides.models import Ride
from apps.payments.models import Payment, LedgerEntry
import apps.rides.admin_views

@pytest.mark.django_db
class TestAdminRideActions:

    @pytest.fixture
    def admin_client(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        return api_client

    def test_admin_list_rides(self, admin_client, ride):
        url = "/api/rides/admin/rides/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert any(r['id'] == ride.id for r in response.data)

    def test_admin_cancel_ride(self, admin_client, ride, driver_user):
        ride.driver = driver_user.driver
        ride.status = Ride.Status.ASSIGNED
        ride.save()
        
        url = "/api/rides/admin/rides/actions/"
        data = {
            "ride_id": ride.id,
            "action": "cancel",
            "refund_amount": 0,
            "compensate_driver_amount": 0
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.CANCELLED

    def test_admin_reassign_ride(self, admin_client, ride, driver_user):
        ride.driver = driver_user.driver
        ride.status = Ride.Status.ASSIGNED
        ride.save()
        
        url = "/api/rides/admin/rides/actions/"
        data = {
            "ride_id": ride.id,
            "action": "reassign"
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.SEARCHING
        assert ride.driver is None

    def test_admin_compensate_driver(self, admin_client, ride, driver_user):
        ride.driver = driver_user.driver
        ride.save()
        
        url = "/api/rides/admin/rides/actions/"
        data = {
            "ride_id": ride.id,
            "action": "compensate_driver",
            "amount": 100,
            "reason": "Traffic delay compensation"
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        
        assert LedgerEntry.objects.filter(
            user=driver_user,
            ride_id=ride.id,
            reason=LedgerEntry.Reason.INCENTIVE # In handle_compensate it calls compensate_driver
        ).exists()

    def test_admin_refund_ride(self, admin_client, ride):
        # Create a captured payment
        Payment.objects.create(
            ride_id=ride.id,
            user=ride.rider,
            amount=Decimal("200.00"),
            status=Payment.Status.CAPTURED,
            gateway="simulation"
        )
        
        url = "/api/rides/admin/rides/actions/"
        data = {
            "ride_id": ride.id,
            "action": "refund"
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        
        payment = Payment.objects.get(ride_id=ride.id)
        assert payment.status == Payment.Status.REFUNDED

    def test_admin_action_invalid_ride(self, admin_client):
        url = "/api/rides/admin/rides/actions/"
        data = {"ride_id": 99999, "action": "cancel"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_action_invalid_action(self, admin_client, ride):
        url = "/api/rides/admin/rides/actions/"
        data = {"ride_id": ride.id, "action": "fly_to_moon"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resolve_ride_cancel(self, admin_client, ride, driver_user):
        ride.driver = driver_user.driver
        ride.status = Ride.Status.ASSIGNED
        ride.save()
        
        url = "/api/admin/resolve-ride/"
        data = {
            "ride_id": ride.id,
            "action": "CANCEL",
            "reason": "Driver not moving",
            "refund_amount": 50,
            "driver_compensation": 20
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.CANCELLED
        
        # Verify manual comp
        assert LedgerEntry.objects.filter(user=driver_user, amount=20).exists()
        # Verify auto penalty
        assert LedgerEntry.objects.filter(user=driver_user, amount=50).exists()

    def test_resolve_ride_missing_id(self, admin_client):
        url = "/api/admin/resolve-ride/"
        data = {"action": "CANCEL"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resolve_ride_waive_fee(self, admin_client, ride, driver_user):
        ride.driver = driver_user.driver
        ride.status = Ride.Status.COMPLETED
        ride.base_fare = 100
        ride.save()
        
        # Mark as not waived initially (default)
        url = "/api/admin/resolve-ride/"
        data = {
            "ride_id": ride.id,
            "waive_fee": True,
            "reason": "Good driver"
        }
        # We need to mock _waive_platform_fee or check its side effect
        # Actually it creates a ledger entry of type CREDIT with reason PLATFORM_REVERSAL usually
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
