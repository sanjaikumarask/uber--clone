import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from apps.rides.models import Ride, RideFeedback
from apps.drivers.models import Driver, DriverStats
from apps.users.models import RiderStats
from apps.rides.fare_models import FareConfig
from apps.payments.models import Payment, DriverEarnings, LedgerEntry
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestViewsCoverageBoost:
    def setup_method(self, method):
        self.client = APIClient()
        name_prefix = method.__name__
        self.rider_user = User.objects.create_user(
            username=f"{name_prefix}_rider", password="password", role="rider"
        )
        self.driver_user = User.objects.create_user(
            username=f"{name_prefix}_driver", password="password", role="driver"
        )
        # Signal might have already created the Driver. Use get_or_create to be safe.
        self.driver, _ = Driver.objects.get_or_create(user=self.driver_user)
        self.driver.is_verified = True
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        self.client.force_authenticate(user=self.rider_user)

    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.logger")
    def test_create_ride_validation_error(self, mock_logger, mock_estimate):
        # Trigger line 121-122: except (KeyError, ValueError, TypeError)
        # We can force a TypeError by making estimate_fare return something that causes a crash later, 
        # but the catch block is before ride object creation.
        # Lines 111-115 call estimate_fare. If we make it raise TypeError:
        mock_estimate.side_effect = TypeError("Mocked type error")
        
        url = "/api/rides/request/"
        data = {
            "pickup_lat": 13.0827, "pickup_lng": 80.2707,
            "drop_lat": 13.0837, "drop_lng": 80.2717,
            "vehicle_type": "go"
        }
        response = self.client.post(url, data)
        assert response.status_code == 400
        assert "Invalid coordinates or missing fields" in response.data["error"]
        mock_logger.error.assert_called()

    @patch("apps.rides.views.find_driver_and_offer_ride")
    @patch("apps.drivers.services.metrics.update_driver_metrics")
    def test_reject_ride_updates_rejected_ids(self, mock_metrics, mock_offer):
        # Trigger line 335-337
        ride = Ride.objects.create(
            rider=self.rider_user, driver=self.driver, 
            status=Ride.Status.OFFERED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1
        )
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/reject/"
        
        # First rejection
        response = self.client.post(url)
        assert response.status_code == 200
        ride.refresh_from_db()
        assert self.driver.id in ride.rejected_driver_ids
        
        # Second rejection (should be already rejected/not eligible but let's re-offer)
        ride.status = Ride.Status.OFFERED
        ride.driver = self.driver
        ride.save()
        response = self.client.post(url)
        assert response.status_code == 200
        ride.refresh_from_db()
        assert ride.rejected_driver_ids.count(self.driver.id) == 1 # Should not append again if already in list (line 335 check)

    @patch("apps.rides.views.verify_and_consume_otp")
    def test_verify_otp_gps_optional_error(self, mock_verify):
        # Trigger line 453-454: except (TypeError, ValueError)
        ride = Ride.objects.create(
            rider=self.rider_user, driver=self.driver, 
            status=Ride.Status.ARRIVED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1
        )
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/start/"
        
        # Invalid lat/lng types
        data = {"otp": "1234", "lat": "invalid", "lng": "invalid"}
        response = self.client.post(url, data)
        assert response.status_code == 200 # GPS is optional, doesn't block start
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ONGOING # Status updated despite GPS error

    def test_update_destination_view(self):
        # Create a valid ongoing ride
        ride = Ride.objects.create(
            rider=self.rider_user, status=Ride.Status.ONGOING,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0
        )
        url = f"/api/rides/{ride.id}/update-destination/"
        data = {"drop_lat": 13.5, "drop_lng": 80.5}
        response = self.client.post(url, data)
        assert response.status_code == 200
        assert response.data["status"] == "UPDATED"
        assert response.data["drop_lat"] == 13.5

    def test_submit_feedback_invalid_role_and_unauthorized(self):
        # Trigger line 675 and 682/699
        ride = Ride.objects.create(
            rider=self.rider_user, driver=self.driver, 
            status=Ride.Status.COMPLETED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1
        )
        # Create another user for unauthorized check
        other_user = User.objects.create_user(
            username="other_feedback_test", password="password", role="rider"
        )
        self.client.force_authenticate(user=other_user)
        
        url = f"/api/rides/{ride.id}/feedback/"
        data = {"rating": 5, "comment": "Great"}
        
        # Unauthorized rider (line 682)
        response = self.client.post(url, data)
        assert response.status_code == 403
        
        # Invalid role (line 675)
        admin_user = User.objects.create_superuser(
            username="admin_feedback_test", password="password", email="admin_feedback@test.com"
        )
        admin_user.role = "admin" # Set a role that is not rider or driver
        admin_user.save()
        self.client.force_authenticate(user=admin_user)
        response = self.client.post(url, data)
        assert response.status_code == 400
        assert response.data["error"] == "Invalid role for feedback"

    def test_submit_feedback_already_submitted(self):
        # Trigger line 702
        ride = Ride.objects.create(
            rider=self.rider_user, driver=self.driver, 
            status=Ride.Status.COMPLETED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1
        )
        # Already has driver feedback
        RideFeedback.objects.create(
            ride=ride, rider=self.rider_user, driver=self.driver,
            giver_role=RideFeedback.GiverRole.DRIVER, rating=5
        )
        
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/feedback/"
        data = {"rating": 5, "comment": "Great"}
        response = self.client.post(url, data)
        assert response.status_code == 400
        assert response.data["error"] == "Feedback already submitted"

    @patch("apps.rides.views._seed_default_fare_configs")
    def test_fare_config_seed_defaults(self, mock_seed):
        # Trigger line 786-791
        FareConfig.objects.all().delete()
        url = "/api/rides/fare-config/"
        response = self.client.get(url)
        assert response.status_code == 200
        mock_seed.assert_called_once()

    def test_tip_view_unauthorized(self):
        # Trigger line 933
        ride = Ride.objects.create(
            rider=self.rider_user, driver=self.driver, 
            status=Ride.Status.COMPLETED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1
        )
        other_rider = User.objects.create_user(
            username="other_rider_tip_test", password="password", role="rider"
        )
        self.client.force_authenticate(user=other_rider)
        
        url = f"/api/rides/{ride.id}/tip/"
        response = self.client.post(url, {"tip_amount": 10})
        assert response.status_code == 403

    def test_tip_view_update_earning(self):
        # Trigger line 972-980
        ride = Ride.objects.create(
            rider=self.rider_user, driver=self.driver, 
            status=Ride.Status.COMPLETED,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1,
            final_fare=100.0, tip_amount=5.0
        )
        Payment.objects.create(ride_id=ride.id, user=self.rider_user, amount=105.0, status=Payment.Status.CAPTURED)
        earning = DriverEarnings.objects.create(
            driver=self.driver, ride=ride, amount=90, commission=10, net_earning=80
        )
        
        self.client.force_authenticate(user=self.rider_user)
        url = f"/api/rides/{ride.id}/tip/"
        # Update tip from 5 to 15 (delta 10)
        response = self.client.post(url, {"tip_amount": 15})
        assert response.status_code == 200
        
        earning.refresh_from_db()
        assert earning.amount == 100 # 90 + 10
        assert earning.net_earning == 90 # 80 + 10
