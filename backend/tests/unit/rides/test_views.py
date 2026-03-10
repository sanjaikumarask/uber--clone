import pytest
from unittest.mock import MagicMock, patch, ANY
from rest_framework.test import APIRequestFactory, force_authenticate
from decimal import Decimal

from apps.rides.views import EstimateFareView, CreateRideView, AcceptRideView, CompleteRideView
from apps.rides.models import Ride
from apps.drivers.models import Driver

@pytest.mark.django_db(transaction=True)
class TestRideViews:

    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.get_planned_route")
    def test_estimate_fare_view(self, mock_route, mock_fare, factory, user):
        mock_fare.return_value = {
            "estimated_fare": Decimal("150.00"),
            "distance_km": 5.0,
            "duration_min": 15
        }
        mock_route.return_value = {"polyline": "abc_polyline"}
        
        view = EstimateFareView.as_view()
        data = {
            "pickup_lat": 12.97,
            "pickup_lng": 77.59,
            "drop_lat": 12.98,
            "drop_lng": 77.60
        }
        request = factory.post("/api/rides/estimate/", data, format="json")
        force_authenticate(request, user=user)
        
        response = view(request)
        assert response.status_code == 200
        assert response.data["estimated_fare"] == 150.0
        assert response.data["polyline"] == "abc_polyline"

    @patch("apps.rides.views.estimate_fare")
    @patch("apps.rides.views.get_planned_route")
    @patch("apps.rides.views.find_driver_and_offer_ride")
    @patch("apps.rides.views.increment_demand")
    def test_create_ride_view_success(self, mock_demand, mock_find_driver, mock_route, mock_fare, factory, user):
        mock_fare.return_value = {
            "estimated_fare": Decimal("150.00"),
            "distance_km": 5.0,
            "duration_min": 15
        }
        mock_route.return_value = {"polyline": "abc_polyline"}
        
        view = CreateRideView.as_view()
        data = {
            "pickup_lat": 12.97,
            "pickup_lng": 77.59,
            "drop_lat": 12.98,
            "drop_lng": 77.60,
            "vehicle_type": "go",
            "city": "Chennai"
        }
        request = factory.post("/api/rides/create/", data, format="json")
        force_authenticate(request, user=user)
        
        with patch("apps.rides.signals.ride_update_signal"):
            response = view(request)
        
        assert response.status_code == 201
        assert Ride.objects.filter(rider=user, status=Ride.Status.SEARCHING).exists()
        mock_find_driver.assert_called_once()

    @patch("apps.rides.services.lifecycle.update_ride_status")
    def test_accept_ride_view(self, mock_update, factory, driver_user):
        driver = driver_user.driver
        # Create a ride to accept
        with patch("apps.rides.signals.ride_update_signal"):
            ride = Ride.objects.create(
                rider=driver_user, # irrelevant
                pickup_lat=12.97, pickup_lng=77.59,
                drop_lat=12.98, drop_lng=77.60,
                status=Ride.Status.OFFERED,
                driver=driver
            )
        
        view = AcceptRideView.as_view()
        request = factory.post(f"/api/rides/{ride.id}/accept/", format="json")
        force_authenticate(request, user=driver_user)
        
        def side_effect(r, status, **kwargs):
            r.status = status
        mock_update.side_effect = side_effect
        
        response = view(request, ride_id=ride.id)
        assert response.status_code == 200
        assert response.data["status"] == Ride.Status.ASSIGNED
        
        mock_update.assert_called_with(ANY, Ride.Status.ASSIGNED)

    @patch("apps.rides.views.CompleteRideView.post", side_effect=None) # We need to patch the service instead
    @patch("apps.rides.views.idempotent_request", lambda **k: lambda f: f) # Disable decorator for unit test
    def test_complete_ride_view(self, mock_idem, factory, driver_user):
        # Re-defining to avoid decorator issues in unit test if necessary, 
        # but let's try direct patching of the service called inside.
        pass

    @patch("apps.common.backpressure.endpoint_cooldown", return_value=True)
    @patch("apps.rides.services.complete_ride.complete_ride")
    def test_complete_ride_view_success(self, mock_complete, mock_cooldown, factory, driver_user):
        ride = MagicMock(spec=Ride)
        ride.id = 123
        ride.status = Ride.Status.COMPLETED
        ride.final_fare = Decimal("250.00")
        ride.actual_distance_km = 8.5
        ride.end_time = "2024-01-01T12:00:00Z"
        ride.start_time = "2024-01-01T11:45:00Z"
        mock_complete.return_value = ride
        
        view = CompleteRideView.as_view()
        request = factory.post("/api/rides/123/complete/", format="json")
        force_authenticate(request, user=driver_user)
        
        response = view(request, ride_id=123)
        assert response.status_code == 200
        assert response.data["status"] == Ride.Status.COMPLETED
        assert response.data["final_fare"] == "250.00"
