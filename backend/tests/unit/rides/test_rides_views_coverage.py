import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.rides.models import Ride
from apps.drivers.models import Driver

@pytest.mark.django_db
class TestRidesViewsCoverage:
    
    @pytest.fixture
    def setup_ride(self, rider_user, driver_user):
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.save()
        ride = Ride.objects.create(
            rider=rider_user,
            pickup_lat=12.9716, pickup_lng=77.5946,
            drop_lat=12.98, drop_lng=77.60,
            status=Ride.Status.SEARCHING
        )
        return ride, rider_user, driver

    def test_estimate_fare_missing_keys(self, authenticated_rider_client):
        url = reverse('ride-estimate')
        data = {"pickup_lat": 12.97} # Missing others
        response = authenticated_rider_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing required fields" in response.data['error']

    def test_estimate_fare_promo_fail(self, authenticated_rider_client):
        url = reverse('ride-estimate')
        data = {
            "pickup_lat": 12.97, "pickup_lng": 77.59,
            "drop_lat": 12.98, "drop_lng": 77.60,
            "promo_code": "FAIL"
        }
        with patch('apps.rides.views.estimate_fare') as mock_est, \
             patch('apps.rides.views.get_planned_route') as mock_route, \
             patch('apps.offers.services.offer_engine.OfferEngine.validate_offer') as mock_val:
            
            mock_est.return_value = {"estimated_fare": Decimal("100.00"), "distance_km": 5, "duration_min": 10}
            mock_route.return_value = {"polyline": "p"}
            mock_val.side_effect = Exception("Offer engine down")
            
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK # It logs and continues
            assert response.data['discount_applied'] == 0

    def test_create_ride_invalid_coords(self, authenticated_rider_client):
        url = reverse('ride-create')
        data = {
            "pickup_lat": 999.0, "pickup_lng": 77.59, # Latitude > 90
            "drop_lat": 12.98, "drop_lng": 77.60
        }
        response = authenticated_rider_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Coordinates out of bounds" in response.data['error']

    def test_create_ride_unexpected_error(self, authenticated_rider_client):
        url = reverse('ride-create')
        data = {"pickup_lat": 12.97, "pickup_lng": 77.59, "drop_lat": 12.98, "drop_lng": 77.60}
        with patch('apps.rides.views.estimate_fare') as mock_est:
            mock_est.side_effect = ZeroDivisionError("Unexpected math error")
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to prepare ride request" in response.data['error']

    def test_accept_ride_throttle(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        url = reverse('ride-accept', kwargs={'ride_id': ride.id})
        with patch('apps.rides.views.endpoint_cooldown') as mock_cool:
            mock_cool.return_value = False
            response = authenticated_driver_client.post(url)
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Too many attempts" in response.data['error']

    def test_apply_promo_unexpected_error(self, authenticated_rider_client):
        # We need a successful ride creation but with promo engine failing
        url = reverse('ride-create')
        data = {
            "pickup_lat": 12.97, "pickup_lng": 77.59,
            "drop_lat": 12.98, "drop_lng": 77.60,
            "promo_code": "BOOM"
        }
        with patch('apps.rides.views.estimate_fare') as mock_est, \
             patch('apps.rides.views.get_planned_route') as mock_route, \
             patch('apps.offers.services.offer_engine.OfferEngine.apply_offer') as mock_apply:
            
            mock_est.return_value = {"estimated_fare": Decimal("100.00"), "distance_km": 5, "duration_min": 10}
            mock_route.return_value = {"polyline": "p"}
            mock_apply.side_effect = Exception("Promo apply failed")
            
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_201_CREATED # It logs and continues
