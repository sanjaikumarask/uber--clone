import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from apps.rides.models import Ride, RideFeedback
from apps.drivers.models import Driver, DriverStats
from apps.rides.fare_models import FareConfig
from apps.payments.models import Payment, DriverEarnings, LedgerEntry
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestRidesViewsComprehensiveV2:
    _counter = 0

    def setup_method(self, method):
        TestRidesViewsComprehensiveV2._counter += 1
        cnt = TestRidesViewsComprehensiveV2._counter
        self.client = APIClient()
        name = method.__name__
        self.rider = User.objects.create_user(username=f"r_{cnt}", role="rider", phone=f"1_{cnt}")
        self.driver_user = User.objects.create_user(username=f"d_{cnt}", role="driver", phone=f"2_{cnt}")
        self.driver, _ = Driver.objects.get_or_create(user=self.driver_user)
        self.driver.is_verified = True
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        self.client.force_authenticate(user=self.rider)

    # --- EstimateFareView tests ---
    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.get_planned_route")
    def test_estimate_fare_success(self, mock_route, mock_estimate):
        mock_estimate.return_value = {"estimated_fare": 100, "distance_km": 5, "duration_min": 10}
        mock_route.return_value = {"polyline": "abc"}
        url = "/api/rides/estimate-fare/"
        data = {"pickup_lat": 13.0, "pickup_lng": 80.0, "drop_lat": 13.1, "drop_lng": 80.1}
        response = self.client.post(url, data)
        assert response.status_code == 200
        assert response.data["estimated_fare"] == 100.0

    def test_estimate_fare_missing_keys(self):
        url = "/api/rides/estimate-fare/"
        response = self.client.post(url, {"pickup_lat": 13.0})
        assert response.status_code == 400
        assert "Missing required fields" in response.data["error"]

    @patch("apps.rides.views.estimate_fare")
    def test_estimate_fare_invalid_coords(self, mock_estimate):
        url = "/api/rides/estimate-fare/"
        response = self.client.post(url, {"pickup_lat": "invalid", "pickup_lng": 80.0, "drop_lat": 13.1, "drop_lng": 80.1})
        assert response.status_code == 400
        assert "Failed to estimate fare" in response.data["error"]

    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.get_planned_route")
    @patch("apps.offers.services.offer_engine.OfferEngine.validate_offer")
    @patch("apps.offers.services.offer_engine.OfferEngine.calculate_discount")
    def test_estimate_fare_with_promo(self, mock_calc, mock_val, mock_route, mock_est):
        mock_est.return_value = {"estimated_fare": 100, "distance_km": 5, "duration_min": 10}
        mock_route.return_value = {"polyline": "abc"}
        mock_val.return_value = MagicMock()
        mock_calc.return_value = 20
        
        url = "/api/rides/estimate-fare/"
        data = {"pickup_lat": 13.0, "pickup_lng": 80.0, "drop_lat": 13.1, "drop_lng": 80.1, "promo_code": "DISCOUNT20"}
        response = self.client.post(url, data)
        assert response.status_code == 200
        assert response.data["discount_applied"] == 20.0
        assert response.data["final_estimate"] == 80.0

    # --- CreateRideView tests ---
    @patch("apps.rides.views.endpoint_cooldown", return_value=False)
    def test_create_ride_rate_limit(self, mock_cooldown):
        url = "/api/rides/request/"
        response = self.client.post(url, {})
        assert response.status_code == 429

    def test_create_ride_active_exists(self):
        Ride.objects.create(rider=self.rider, status=Ride.Status.SEARCHING, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = "/api/rides/request/"
        response = self.client.post(url, {})
        assert response.status_code == 409

    def test_create_ride_invalid_coords_range(self):
        url = "/api/rides/request/"
        data = {"pickup_lat": 100, "pickup_lng": 0, "drop_lat": 0, "drop_lng": 0}
        response = self.client.post(url, data)
        assert response.status_code == 400
        assert response.data["error"] == "Coordinates out of bounds"

    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.get_planned_route")
    @patch("apps.rides.views.find_driver_and_offer_ride")
    def test_create_ride_success(self, mock_find, mock_route, mock_est):
        mock_est.return_value = {"estimated_fare": 100, "distance_km": 5, "duration_min": 10}
        mock_route.return_value = {"polyline": "abc"}
        url = "/api/rides/request/"
        data = {"pickup_lat": 13, "pickup_lng": 80, "drop_lat": 13.1, "drop_lng": 80.1, "vehicle_type": "go"}
        response = self.client.post(url, data)
        assert response.status_code == 201
        assert response.data["status"] == "SEARCHING"

    # --- RideDetailView tests ---
    def test_ride_detail_not_found(self):
        url = "/api/rides/9999/"
        response = self.client.get(url)
        assert response.status_code == 404

    def test_ride_detail_unauthorized(self):
        other = User.objects.create_user(username="other_detail", role="rider")
        ride = Ride.objects.create(rider=other, status=Ride.Status.SEARCHING, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = f"/api/rides/{ride.id}/"
        response = self.client.get(url)
        assert response.status_code == 403

    # --- AcceptRideView tests ---
    def test_accept_ride_wrong_status(self):
        ride = Ride.objects.create(rider=self.rider, status=Ride.Status.SEARCHING, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/accept/"
        response = self.client.post(url)
        assert response.status_code == 400
        assert "Status is SEARCHING" in response.data["error"]

    def test_accept_ride_already_assigned(self):
        other_driver_user = User.objects.create_user(username="other_driver_acc", role="driver")
        other_driver, _ = Driver.objects.get_or_create(user=other_driver_user)
        ride = Ride.objects.create(rider=self.rider, driver=other_driver, status=Ride.Status.OFFERED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/accept/"
        response = self.client.post(url)
        assert response.status_code == 400
        assert "NOT assigned to you" in response.data["error"]

    # --- DriverArrivedView tests ---
    def test_driver_arrived_wrong_driver(self):
        ride = Ride.objects.create(rider=self.rider, driver=self.driver, status=Ride.Status.ASSIGNED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        other_driver_user = User.objects.create_user(username="evil_driver_arr", role="driver")
        self.client.force_authenticate(user=other_driver_user)
        url = f"/api/rides/{ride.id}/arrived/"
        response = self.client.post(url)
        assert response.status_code == 404 # get_object_or_404 with driver filter returns 404

    # --- VerifyOtpView tests ---
    @patch("apps.rides.views.verify_and_consume_otp")
    def test_verify_otp_invalid(self, mock_verify):
        from rest_framework.exceptions import ValidationError
        mock_verify.side_effect = ValidationError("Invalid OTP")
        ride = Ride.objects.create(rider=self.rider, driver=self.driver, status=Ride.Status.ARRIVED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/start/"
        response = self.client.post(url, {"otp": "0000"})
        assert response.status_code == 400

    # --- CancelRideView tests ---
    def test_cancel_ride_completed(self):
        ride = Ride.objects.create(rider=self.rider, status=Ride.Status.COMPLETED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = f"/api/rides/{ride.id}/cancel/"
        response = self.client.post(url)
        assert response.status_code == 400
        # Check if error is in a list or dict
        if isinstance(response.data, list):
            assert "cannot be cancelled" in response.data[0]
        else:
            assert "cannot be cancelled" in response.data["error"]

    # --- NearbyDriversView tests ---
    @patch("apps.drivers.services.geo.get_nearby_driver_ids")
    def test_nearby_drivers_success(self, mock_nearby):
        mock_nearby.return_value = [self.driver.id]
        url = "/api/rides/nearby-drivers/"
        data = {"lat": 13, "lng": 80}
        response = self.client.post(url, data)
        assert response.status_code == 200
        assert len(response.data["drivers"]) == 1

    # --- RideHistoryView tests ---
    def test_ride_history_rider(self):
        Ride.objects.create(rider=self.rider, status=Ride.Status.COMPLETED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = "/api/rides/history/"
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_ride_history_driver(self):
        Ride.objects.create(rider=self.rider, driver=self.driver, status=Ride.Status.COMPLETED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        self.client.force_authenticate(user=self.driver_user)
        url = "/api/rides/history/"
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1

    # --- ActiveRideView tests ---
    def test_active_ride_none(self):
        url = "/api/rides/active/"
        response = self.client.get(url)
        assert response.status_code == 200
        # If it returns {"id": None} or None
        if response.data:
            assert response.data.get("id") is None
        else:
            assert response.data is None

    def test_active_ride_found(self):
        ride = Ride.objects.create(rider=self.rider, status=Ride.Status.SEARCHING, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = "/api/rides/active/"
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["id"] == ride.id

    # --- RejectRideView tests ---
    def test_reject_ride_not_found(self):
        url = "/api/rides/9999/reject/"
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(url)
        assert response.status_code == 400
        assert "not eligible for rejection" in response.data["error"]

    def test_reject_ride_success(self):
        ride = Ride.objects.create(rider=self.rider, driver=self.driver, status=Ride.Status.OFFERED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/reject/"
        with patch("apps.drivers.services.metrics.update_driver_metrics") as mock_metrics:
            response = self.client.post(url)
            assert response.status_code == 200
            ride.refresh_from_db()
            assert ride.status == Ride.Status.SEARCHING
            assert ride.driver is None

    # --- EstimateFareView edge cases ---
    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.get_planned_route")
    @patch("apps.offers.services.offer_engine.OfferEngine.validate_offer")
    def test_estimate_fare_promo_failure(self, mock_val, mock_route, mock_est):
        mock_est.return_value = {"estimated_fare": 100, "distance_km": 5, "duration_min": 10}
        mock_route.return_value = {"polyline": "abc"}
        mock_val.side_effect = Exception("Promo expired")
        url = "/api/rides/estimate-fare/"
        data = {"pickup_lat": 13, "pickup_lng": 80, "drop_lat": 13.1, "drop_lng": 80.1, "promo_code": "EXPIRED"}
        response = self.client.post(url, data)
        assert response.status_code == 200
        assert response.data["discount_applied"] == 0.0

    # --- CreateRideView edge cases ---
    @patch("apps.rides.views.estimate_fare")
    def test_create_ride_unexpected_error(self, mock_est):
        mock_est.side_effect = Exception("General error")
        url = "/api/rides/request/"
        data = {"pickup_lat": 13, "pickup_lng": 80, "drop_lat": 13.1, "drop_lng": 80.1}
        response = self.client.post(url, data)
        assert response.status_code == 500
        assert "Failed to prepare ride request" in response.data["error"]

    # --- OTP Brute Force test ---
    @patch("apps.drivers.redis.redis_client.get")
    def test_verify_otp_brute_force(self, mock_get):
        mock_get.return_value = "5"
        ride = Ride.objects.create(rider=self.rider, driver=self.driver, status=Ride.Status.ARRIVED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        self.client.force_authenticate(user=self.driver_user)
        url = f"/api/rides/{ride.id}/start/"
        response = self.client.post(url, {"otp": "1234"})
        assert response.status_code == 429
        assert "Too many failed OTP attempts" in response.data["error"]
        ride.refresh_from_db()
        assert ride.is_fraud_flagged

    # --- UpdateDestinationView tests ---
    def test_update_destination_not_ongoing(self):
        ride = Ride.objects.create(rider=self.rider, status=Ride.Status.SEARCHING, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = f"/api/rides/{ride.id}/update-destination/"
        response = self.client.post(url, {"drop_lat": 1, "drop_lng": 1})
        assert response.status_code == 400
        assert "is not ONGOING" in response.data["error"]

    # --- SubmitFeedbackView tests ---
    def test_submit_feedback_success(self):
        ride = Ride.objects.create(rider=self.rider, driver=self.driver, status=Ride.Status.COMPLETED, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        url = f"/api/rides/{ride.id}/feedback/"
        response = self.client.post(url, {"rating": 5, "comment": "Great!"})
        assert response.status_code == 200
        assert RideFeedback.objects.filter(ride=ride).exists()
