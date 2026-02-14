"""
Unit and Integration Tests for Driver Functionality
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from django.db import models
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from apps.drivers.models import Driver
from apps.rides.models import Ride

User = get_user_model()


@pytest.mark.django_db
class TestDriverModel:
    """Test Driver model"""

    def setup_method(self):
        self.driver_user = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="pass123",
            role="driver"
        )
        self.driver = Driver.objects.get(user=self.driver_user)

    def test_driver_created_on_user_creation(self):
        """Test that driver profile is created automatically"""
        assert self.driver is not None
        assert self.driver.user == self.driver_user

    def test_driver_default_status(self):
        """Test driver default status"""
        assert self.driver.status == Driver.Status.OFFLINE

    def test_driver_go_online(self):
        """Test driver going online"""
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        
        assert self.driver.status == Driver.Status.ONLINE

    def test_driver_location_update(self):
        """Test updating driver location"""
        self.driver.last_lat = 13.0827
        self.driver.last_lng = 80.2707
        self.driver.save()
        
        assert self.driver.last_lat == 13.0827
        assert self.driver.last_lng == 80.2707

    def test_driver_string_representation(self):
        """Test driver __str__ method"""
        assert str(self.driver) == f"Driver #{self.driver.id} ({self.driver.status})"


@pytest.mark.django_db
class TestDriverStatus:
    """Test driver status management"""

    def setup_method(self):
        self.client = APIClient()
        self.driver_user = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="pass123",
            role="driver"
        )
        self.driver = Driver.objects.get(user=self.driver_user)

    def test_update_status_to_online(self):
        """Test updating driver status to online"""
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(
            "/api/drivers/status/",
            {"status": "ONLINE"},
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        self.driver.refresh_from_db()
        assert self.driver.status == Driver.Status.ONLINE

    def test_update_status_to_offline(self):
        """Test updating driver status to offline"""
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(
            "/api/drivers/status/",
            {"status": "OFFLINE"},
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        self.driver.refresh_from_db()
        assert self.driver.status == Driver.Status.OFFLINE

    def test_update_status_unauthenticated(self):
        """Test updating status without authentication"""
        response = self.client.post(
            "/api/drivers/status/",
            {"status": "ONLINE"},
            format="json"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_driver_cannot_update_status(self):
        """Test that non-driver cannot update driver status"""
        rider = User.objects.create_user(
            username="rider",
            phone="9876543210",
            password="pass123",
            role="rider"
        )
        
        self.client.force_authenticate(user=rider)
        
        response = self.client.post(
            "/api/drivers/status/",
            {"status": "ONLINE"},
            format="json"
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDriverLocation:
    """Test driver location tracking"""

    def setup_method(self):
        self.client = APIClient()
        self.driver_user = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="pass123",
            role="driver"
        )
        self.driver = Driver.objects.get(user=self.driver_user)

    def test_update_location(self):
        """Test updating driver location"""
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(
            "/api/tracking/update-location/",
            {
                "lat": 13.0827,
                "lng": 80.2707
            },
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        self.driver.refresh_from_db()
        assert self.driver.last_lat == 13.0827
        assert self.driver.last_lng == 80.2707

    def test_update_location_invalid_coordinates(self):
        """Test updating location with invalid coordinates"""
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(
            "/api/tracking/update-location/",
            {
                "lat": 200,  # Invalid
                "lng": 80.2707
            },
            format="json"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_nearby_drivers(self):
        """Test getting nearby drivers"""
        # Set driver location
        self.driver.last_lat = 13.0827
        self.driver.last_lng = 80.2707
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        
        # This would typically be called internally
        # Testing the query logic
        nearby = Driver.objects.filter(
            status=Driver.Status.ONLINE,
            last_lat__isnull=False,
            last_lng__isnull=False
        )
        
        assert self.driver in nearby


@pytest.mark.django_db
class TestDriverRideManagement:
    """Test driver ride management"""

    def setup_method(self):
        self.client = APIClient()
        self.rider = User.objects.create_user(
            username="rider",
            phone="9876543210",
            password="pass123",
            role="rider"
        )
        self.driver_user = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="pass123",
            role="driver"
        )
        self.driver = Driver.objects.get(user=self.driver_user)

    def test_driver_accept_ride(self):
        """Test driver accepting a ride"""
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.OFFERED,
            driver=self.driver
        )
        
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(f"/api/rides/{ride.id}/accept/")
        
        assert response.status_code == status.HTTP_200_OK
        
        ride.refresh_from_db()
        assert ride.driver == self.driver
        assert ride.status == Ride.Status.ASSIGNED

    def test_driver_reject_ride(self):
        """Test driver rejecting a ride"""
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.OFFERED,
            driver=self.driver
        )
        
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.post(f"/api/rides/{ride.id}/reject/")
        
        assert response.status_code == status.HTTP_200_OK
        
        ride.refresh_from_db()
        assert ride.driver is None

    def test_driver_get_active_ride(self):
        """Test driver getting their active ride"""
        ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.ONGOING
        )
        
        self.client.force_authenticate(user=self.driver_user)
        
        response = self.client.get("/api/drivers/active-ride/")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == ride.id

    def test_driver_earnings(self):
        """Test driver earnings calculation"""
        # Create completed rides
        for i in range(3):
            Ride.objects.create(
                rider=self.rider,
                driver=self.driver,
                pickup_lat=13.0827,
                pickup_lng=80.2707,
                drop_lat=13.0569,
                drop_lng=80.2425,
                status=Ride.Status.COMPLETED,
                final_fare=Decimal("100.00")
            )
        
        total_earnings = Ride.objects.filter(
            driver=self.driver,
            status=Ride.Status.COMPLETED
        ).aggregate(total=models.Sum('final_fare'))['total']
        
        assert total_earnings == Decimal("300.00")


@pytest.mark.django_db
class TestDriverStatistics:
    """Test driver statistics"""

    def setup_method(self):
        self.rider = User.objects.create_user(
            username="rider",
            phone="9876543210",
            password="pass123",
            role="rider"
        )
        self.driver_user = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="pass123",
            role="driver"
        )
        self.driver = Driver.objects.get(user=self.driver_user)

    def test_total_rides_count(self):
        """Test counting total rides"""
        # Create rides
        for i in range(5):
            Ride.objects.create(
                rider=self.rider,
                driver=self.driver,
                pickup_lat=13.0827,
                pickup_lng=80.2707,
                drop_lat=13.0569,
                drop_lng=80.2425,
                status=Ride.Status.COMPLETED
            )
        
        total_rides = Ride.objects.filter(driver=self.driver).count()
        
        assert total_rides == 5

    def test_completed_rides_count(self):
        """Test counting completed rides"""
        # Create completed rides
        for i in range(3):
            Ride.objects.create(
                rider=self.rider,
                driver=self.driver,
                pickup_lat=13.0827,
                pickup_lng=80.2707,
                drop_lat=13.0569,
                drop_lng=80.2425,
                status=Ride.Status.COMPLETED
            )
        
        # Create cancelled ride
        Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.CANCELLED
        )
        
        completed = Ride.objects.filter(
            driver=self.driver,
            status=Ride.Status.COMPLETED
        ).count()
        
        assert completed == 3
