import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.rides.models import Ride
from apps.drivers.models import Driver
import apps.rides.views

@pytest.mark.django_db
class TestRidesEdgeCases:
    
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
    
    def test_estimate_fare_with_promo(self, authenticated_rider_client):
        url = reverse('ride-estimate')
        data = {
            "pickup_lat": 12.97, "pickup_lng": 77.59,
            "drop_lat": 12.98, "drop_lng": 77.60,
            "promo_code": "SAVE50"
        }
        with patch('apps.rides.views.estimate_fare') as mock_est, \
             patch('apps.rides.views.get_planned_route') as mock_route, \
             patch('apps.offers.services.offer_engine.OfferEngine.validate_offer') as mock_val, \
             patch('apps.offers.services.offer_engine.OfferEngine.calculate_discount') as mock_disc:
            
            mock_est.return_value = {"estimated_fare": Decimal("100.00"), "distance_km": 5, "duration_min": 10}
            mock_route.return_value = {"polyline": "p"}
            mock_val.return_value = MagicMock()
            mock_disc.return_value = Decimal("20.00")
            
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['discount_applied'] == 20.0
            assert response.data['final_estimate'] == 80.0

    def test_create_ride_active_exists(self, authenticated_rider_client, rider_user):
        # Create an active ride
        Ride.objects.create(
            rider=rider_user,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0,
            status=Ride.Status.SEARCHING
        )
        url = reverse('ride-create')
        data = {"pickup_lat": 1, "pickup_lng": 1, "drop_lat": 1, "drop_lng": 1}
        response = authenticated_rider_client.post(url, data)
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_ride_missing_coords(self, authenticated_rider_client):
        url = reverse('ride-create')
        data = {"pickup_lat": 1} # Missing others
        response = authenticated_rider_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_otp_throttle(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.ARRIVED
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-start', kwargs={'ride_id': ride.id})
        with patch('apps.rides.views.endpoint_cooldown') as mock_cool:
            mock_cool.return_value = False
            response = authenticated_driver_client.post(url, {"otp": "1234"})
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_verify_otp_brute_force(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.ARRIVED
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-start', kwargs={'ride_id': ride.id})
        with patch('apps.drivers.redis.redis_client.get') as mock_get:
            mock_get.return_value = b"5" # 5 attempts already
            response = authenticated_driver_client.post(url, {"otp": "1234"})
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            ride.refresh_from_db()
            assert ride.is_fraud_flagged is True
