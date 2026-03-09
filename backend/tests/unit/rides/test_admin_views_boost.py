import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.payments.models import Payment, LedgerEntry
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestAdminViewsBoost:
    def setup_method(self, method):
        self.client = APIClient()
        name = method.__name__
        self.admin_user = User.objects.create_superuser(username=f"{name}_admin", password="password", email=f"{name}@test.com")
        # Ensure role is 'admin' if your IsAdmin permission checks for it
        self.admin_user.role = "admin"
        self.admin_user.save()
        
        self.rider = User.objects.create_user(username=f"{name}_rider", role="rider")
        self.driver_user = User.objects.create_user(username=f"{name}_driver", role="driver")
        self.driver, _ = Driver.objects.get_or_create(user=self.driver_user)
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        
        self.ride = Ride.objects.create(
            rider=self.rider, driver=self.driver, status=Ride.Status.OFFERED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1, base_fare=100
        )
        self.client.force_authenticate(user=self.admin_user)

    @patch("apps.rides.admin_views.Ride.objects.get")
    def test_admin_ride_action_generic_exception(self, mock_get):
        # Trigger line 79-81
        mock_get.side_effect = Exception("General failure")
        url = "/api/rides/admin/rides/actions/"
        # Or if it's imported in a way that needs different URL
        # Assuming URL patterned in admin_dashboard/urls.py or rides/urls.py
        
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "cancel"})
        assert response.status_code == 400
        assert response.data["error"] == "General failure"

    def test_handle_cancel_no_payment_coverage(self):
        # Trigger line 112-116
        # Ride has no payment
        url = "/api/rides/admin/rides/actions/"
        data = {"ride_id": self.ride.id, "action": "cancel", "refund_amount": 50, "compensate_driver_amount": 20}
        
        with patch("apps.rides.admin_views.service_cancel_ride") as mock_cancel:
            response = self.client.post(url, data)
            assert response.status_code == 200
            mock_cancel.assert_called_once()
            # Refund should not be called as no payment exists

    def test_handle_compensate_errors(self):
        # Trigger line 123 (amount <= 0)
        url = "/api/rides/admin/rides/actions/"
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "compensate_driver", "amount": 0})
        assert response.status_code == 400
        assert response.data["error"] == "Amount required"
        
        # Trigger line 125 (no driver)
        self.ride.driver = None
        self.ride.save()
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "compensate_driver", "amount": 10})
        assert response.status_code == 400
        assert response.data["error"] == "No driver assigned to this ride"

    def test_handle_reassign_invalid_status_and_driver_cleanup(self):
        # Trigger line 139 (invalid status)
        self.ride.status = Ride.Status.COMPLETED
        self.ride.save()
        url = "/api/rides/admin/rides/actions/"
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "reassign"})
        assert response.status_code == 400
        assert response.data["error"] == "Ride is not in a reassignable state"
        
        # Trigger line 148-152 (driver cleanup)
        self.ride.status = Ride.Status.ASSIGNED
        self.driver.status = Driver.Status.BUSY
        self.driver.save()
        self.ride.save()
        
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "reassign"})
        assert response.status_code == 200
        self.driver.refresh_from_db()
        assert self.driver.status == "ONLINE"

    @patch("apps.rides.admin_views.Ride.objects.select_for_update")
    def test_resolve_ride_view_exception(self, mock_select):
        # Trigger line 190-192
        mock_select.return_value.get.side_effect = Exception("Resolution crash")
        url = "/api/admin/resolve-ride/"
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "CANCEL"})
        assert response.status_code == 500
        assert response.data["error"] == "Resolution crash"

    def test_get_resolution_params_coverage(self):
        # Trigger line 198, 200-201
        url = "/api/admin/resolve-ride/"
        # Sending non-numeric values
        data = {
            "ride_id": self.ride.id,
            "action": "CANCEL",
            "refund_amount": "invalid",
            "driver_compensation": "",
            "penalty_amount": "NaN"
        }
        response = self.client.post(url, data)
        assert response.status_code == 200
        # Should have defaulted to 0.00 without crashing

    def test_refund_rider_no_payment_ledger_fallback(self):
        # Trigger line 243-244 (Wait, line 243-244 is IF payment. Let's trigger ELSE)
        # Line 245-253 is the ELSE block
        url = "/api/admin/resolve-ride/"
        data = {
            "ride_id": self.ride.id,
            "action": "RESOLVE",
            "refund_amount": 50
        }
        # Ride has no payment
        response = self.client.post(url, data)
        assert response.status_code == 200
        
        # Check if ledger entry was created for the rider (credit)
        ledger = LedgerEntry.objects.filter(user=self.rider, ride_id=self.ride.id).first()
        assert ledger is not None
        assert ledger.entry_type == LedgerEntry.Type.CREDIT
        assert ledger.amount == 50

    def test_admin_rides_list_view_success(self):
        """Trigger lines 14-38: list rides with various driver/payment states."""
        # Create a ride with payment
        p = Payment.objects.create(ride_id=self.ride.id, user=self.rider, amount=100, status=Payment.Status.CAPTURED)
        
        # Create a ride without a driver
        Ride.objects.create(rider=self.rider, status=Ride.Status.SEARCHING, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        
        url = "/api/rides/admin/rides/" # Adjust if prefix is different
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.data) >= 2
        # Check if it correctly handles missing driver (line 30)
        assert any(r["driver_phone"] is None for r in response.data)

    def test_admin_ride_action_missing_id(self):
        """Trigger lines 59-62: missing ride_id."""
        url = "/api/rides/admin/rides/actions/"
        response = self.client.post(url, {"action": "cancel"})
        assert response.status_code == 400
        assert "ride_id is required" in response.data["error"]

    def test_admin_ride_action_invalid_action(self):
        """Trigger lines 64-67: invalid action."""
        url = "/api/rides/admin/rides/actions/"
        response = self.client.post(url, {"ride_id": self.ride.id, "action": "explode"})
        assert response.status_code == 400
        assert "Invalid action" in response.data["error"]

    def test_admin_ride_action_not_found(self):
        """Trigger lines 73-77: ride not found."""
        url = "/api/rides/admin/rides/actions/"
        response = self.client.post(url, {"ride_id": 9999, "action": "cancel"})
        assert response.status_code == 404
        assert "Ride not found" in response.data["error"]
