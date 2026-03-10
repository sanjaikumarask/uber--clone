import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.users.models import User

@pytest.mark.django_db
class TestRidesViewsErrorPaths:
    
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

    @pytest.fixture
    def other_rider_user(self, db):
        return User.objects.create_user(username="other_rider", phone="9999999999", role="rider")

    @pytest.fixture
    def other_driver_user(self, db):
        user = User.objects.create_user(username="other_driver", phone="8888888888", role="driver")
        Driver.objects.get_or_create(user=user)
        return user

    def test_estimate_fare_service_error(self, authenticated_rider_client):
        url = reverse('ride-estimate')
        data = {"pickup_lat": 12.97, "pickup_lng": 77.59, "drop_lat": 12.98, "drop_lng": 77.60}
        with patch('apps.rides.views.estimate_fare') as mock_est:
            mock_est.side_effect = Exception("Service unavailable")
            response = authenticated_rider_client.post(url, data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_ride_database_error(self, authenticated_rider_client):
        url = reverse('ride-create')
        data = {"pickup_lat": 12.97, "pickup_lng": 77.59, "drop_lat": 12.98, "drop_lng": 77.60}
        with patch('apps.rides.models.Ride.objects.create') as mock_create:
            mock_create.side_effect = Exception("DB error")
            response = authenticated_rider_client.post(url, data)
            assert response.status_code in [400, 500]

    def test_ride_detail_forbidden(self, api_client, other_rider_user, setup_ride):
        ride, rider, driver = setup_ride
        api_client.force_authenticate(user=other_rider_user)
        url = reverse('ride-detail', kwargs={'ride_id': ride.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accept_ride_no_driver_permission(self, authenticated_rider_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.OFFERED
        ride.save()
        url = reverse('ride-accept', kwargs={'ride_id': ride.id})
        response = authenticated_rider_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_driver_arrived_wrong_driver(self, api_client, other_driver_user, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.ASSIGNED
        ride.driver = other_driver_user.driver
        ride.save()
        
        third_driver = User.objects.create_user(username="third_driver", phone="1111111111", role="driver")
        Driver.objects.get_or_create(user=third_driver)
        api_client.force_authenticate(user=third_driver)
        
        url = reverse('ride-arrive', kwargs={'ride_id': ride.id})
        response = api_client.post(url)
        # DriverArrivedView uses get_object_or_404(driver__user=request.user) -> 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_otp_wrong_status(self, authenticated_driver_client, setup_ride):
        ride, rider, driver = setup_ride
        ride.status = Ride.Status.ASSIGNED 
        ride.driver = driver
        ride.save()
        
        url = reverse('ride-start', kwargs={'ride_id': ride.id})
        response = authenticated_driver_client.post(url, {"otp": "1234"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
