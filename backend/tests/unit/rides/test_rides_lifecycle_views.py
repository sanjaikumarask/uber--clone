import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.users.models import User
from apps.rides.services.otp import generate_and_attach_otp
import apps.rides.views

@pytest.mark.django_db
class TestRidesLifecycleViews:
    
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

    def test_estimate_fare_view(self, authenticated_rider_client):
        url = reverse('ride-estimate')
        data = {
            "pickup_lat": 12.9716, "pickup_lng": 77.5946,
            "drop_lat": 12.98, "drop_lng": 77.60
        }
        with patch('apps.rides.views.estimate_fare') as mock_est, \
             patch('apps.rides.views.get_planned_route') as mock_route:
            mock_est.return_value = {
                "estimated_fare": Decimal("150.00"),
                "distance_km": 5.5,
                "duration_min": 15
            }
            mock_route.return_value = {"polyline": "abc_polyline"}
            
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['estimated_fare'] == 150.0

    def test_create_ride_view(self, authenticated_rider_client, rider_user):
        url = reverse('ride-create')
        data = {
            "pickup_lat": 12.9716, "pickup_lng": 77.5946,
            "drop_lat": 12.98, "drop_lng": 77.60,
            "vehicle_type": "go"
        }
        # Mocking services that are called during creation
        with patch('apps.rides.views.estimate_fare') as mock_est, \
             patch('apps.rides.views.get_planned_route') as mock_route, \
             patch('apps.rides.views.find_driver_and_offer_ride') as mock_matching, \
             patch('apps.rides.views.increment_demand'):
            
            mock_est.return_value = {
                "estimated_fare": Decimal("150.00"),
                "distance_km": 5.5,
                "duration_min": 15
            }
            mock_route.return_value = {"polyline": "abc_polyline"}
            
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_201_CREATED
            assert Ride.objects.filter(rider__id=rider_user.id).exists()

    def test_accept_ride_view(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        # Move ride to OFFERED and assign to driver
        ride.status = Ride.Status.OFFERED
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-accept', kwargs={'ride_id': ride.id})
        response = authenticated_driver_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED
        driver.refresh_from_db()
        assert driver.status == Driver.Status.BUSY

    def test_reject_ride_view(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.OFFERED
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-reject', kwargs={'ride_id': ride.id})
        with patch('apps.rides.views.find_driver_and_offer_ride') as mock_matching:
            response = authenticated_driver_client.post(url)
            assert response.status_code == status.HTTP_200_OK
            ride.refresh_from_db()
            assert ride.status == Ride.Status.SEARCHING
            assert ride.driver is None
            assert driver.id in ride.rejected_driver_ids

    def test_driver_arrived_view(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.ASSIGNED
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-arrive', kwargs={'ride_id': ride.id})
        response = authenticated_driver_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ARRIVED

    def test_verify_otp_view(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        # Ensure OTP exists
        ride.status = Ride.Status.ASSIGNED
        ride.driver = driver
        ride.save()
        otp_code = generate_and_attach_otp(ride)
        
        ride.status = Ride.Status.ARRIVED
        ride.save()
        
        url = reverse('ride-start', kwargs={'ride_id': ride.id})
        data = {"otp": otp_code, "lat": 12.97, "lng": 77.59}
        response = authenticated_driver_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ONGOING
        assert ride.start_time is not None

    def test_complete_ride_view(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.ONGOING
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-complete', kwargs={'ride_id': ride.id})
        with patch('apps.rides.services.complete_ride.complete_ride') as mock_complete:
            mock_complete.return_value = ride
            response = authenticated_driver_client.post(url)
            assert response.status_code == status.HTTP_200_OK
    def test_create_ride_rate_limit(self, authenticated_rider_client):
        url = reverse('ride-create')
        data = {"pickup_lat": 12.97, "pickup_lng": 77.59, "drop_lat": 12.98, "drop_lng": 77.60}
        
        with patch('apps.rides.views.endpoint_cooldown') as mock_cooldown:
            mock_cooldown.return_value = False
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_accept_ride_not_found(self, authenticated_driver_client):
        url = reverse('ride-accept', kwargs={'ride_id': 9999})
        response = authenticated_driver_client.post(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_accept_ride_wrong_status(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.COMPLETED
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-accept', kwargs={'ride_id': ride.id})
        response = authenticated_driver_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Status is COMPLETED" in response.data['error']
