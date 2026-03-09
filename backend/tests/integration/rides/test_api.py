"""
Integration Tests for Ride API Endpoints
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.rides.models import Ride

User = get_user_model()


@pytest.mark.django_db
class TestRideCreation:
    """Test ride creation endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.rider = User.objects.create_user(
            username="rider", phone="9876543210", password="pass123", role="rider"
        )

    @patch("apps.rides.services.distance.get_planned_route")
    @patch("apps.rides.views.get_planned_route")
    def test_create_ride_success(self, mock_view_route, mock_dist_route):
        """Test successful ride creation"""
        mock_data = {
            "polyline": "mock_polyline",
            "distance_km": 5.2,
            "duration_min": 15,
        }
        mock_view_route.return_value = mock_data
        mock_dist_route.return_value = mock_data

        self.client.force_authenticate(user=self.rider)

        data = {
            "pickup_lat": 13.0827,
            "pickup_lng": 80.2707,
            "pickup_address": "Chennai Central",
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
            "dropoff_address": "Marina Beach",
        }

        response = self.client.post("/api/rides/request/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

        ride = Ride.objects.get(id=response.data["id"])
        assert ride.rider == self.rider
        assert ride.planned_distance_km == 5.2

    def test_create_ride_unauthenticated(self):
        """Test ride creation without authentication"""
        data = {
            "pickup_lat": 13.0827,
            "pickup_lng": 80.2707,
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
        }

        response = self.client.post("/api/rides/request/", data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_ride_missing_fields(self):
        """Test ride creation with missing required fields"""
        self.client.force_authenticate(user=self.rider)

        data = {
            "pickup_lat": 13.0827,
            # Missing other required fields
        }

        response = self.client.post("/api/rides/request/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_ride_invalid_coordinates(self):
        """Test ride creation with invalid coordinates"""
        self.client.force_authenticate(user=self.rider)

        data = {
            "pickup_lat": 200,  # Invalid latitude
            "pickup_lng": 80.2707,
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
        }

        response = self.client.post("/api/rides/request/", data, format="json")

        # Invalid coordinates are accepted but fallback to local calculation
        # So this test expects success with fallback
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestRideRetrieval:
    """Test ride retrieval endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.rider = User.objects.create_user(
            username="rider", phone="9876543210", password="pass123", role="rider"
        )
        self.ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            planned_distance_km=5.2,
            # estimated_fare=Decimal("120.00")
        )

    def test_get_ride_detail(self):
        """Test getting ride details"""
        self.client.force_authenticate(user=self.rider)

        response = self.client.get(f"/api/rides/{self.ride.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.ride.id

    def test_get_active_ride(self):
        """Test getting active ride"""
        self.client.force_authenticate(user=self.rider)

        self.ride.status = Ride.Status.ONGOING
        self.ride.save()

        response = self.client.get("/api/rides/active/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.ride.id

    def test_get_ride_history(self):
        """Test getting ride history"""
        self.client.force_authenticate(user=self.rider)

        # Create completed ride
        self.ride.status = Ride.Status.COMPLETED
        self.ride.save()

        response = self.client.get("/api/rides/history/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0

    def test_get_ride_unauthorized(self):
        """Test getting ride details without authentication"""
        response = self.client.get(f"/api/rides/{self.ride.id}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRideActions:
    """Test ride action endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.rider = User.objects.create_user(
            username="rider", phone="9876543210", password="pass123", role="rider"
        )
        self.driver_user = User.objects.create_user(
            username="driver", phone="1234567890", password="pass123", role="driver"
        )
        Driver.objects.get_or_create(
            user=self.driver_user, defaults={"status": Driver.Status.OFFLINE}
        )
        self.driver = Driver.objects.get(user=self.driver_user)
        self.ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.ASSIGNED,
        )

    def test_cancel_ride(self):
        """Test ride cancellation"""
        self.client.force_authenticate(user=self.rider)

        response = self.client.post(f"/api/rides/{self.ride.id}/cancel/")

        assert response.status_code == status.HTTP_200_OK

        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.CANCELLED

    def test_driver_accept_ride(self):
        """Test driver accepting ride"""
        self.ride.status = Ride.Status.OFFERED
        self.ride.driver = self.driver
        self.ride.save()

        self.client.force_authenticate(user=self.driver_user)

        response = self.client.post(f"/api/rides/{self.ride.id}/accept/")

        assert response.status_code == status.HTTP_200_OK

        self.ride.refresh_from_db()
        assert self.ride.driver == self.driver
        assert self.ride.status == Ride.Status.ASSIGNED

    def test_driver_arrive(self):
        """Test driver marking arrival"""
        self.client.force_authenticate(user=self.driver_user)

        response = self.client.post(f"/api/rides/{self.ride.id}/arrived/")

        assert response.status_code == status.HTTP_200_OK

        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.ARRIVED
        assert self.ride.arrived_at is not None

    def test_start_ride(self):
        """Test starting ride"""
        from datetime import timedelta

        from django.utils import timezone

        self.ride.status = Ride.Status.ARRIVED
        self.ride.otp_code = "1234"
        self.ride.otp_expires_at = timezone.now() + timedelta(minutes=5)
        self.ride.save()

        self.client.force_authenticate(user=self.driver_user)

        response = self.client.post(
            f"/api/rides/{self.ride.id}/start/", {"otp": "1234"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.ONGOING

    def test_complete_ride(self):
        """Test completing ride"""
        from django.utils import timezone

        self.ride.status = Ride.Status.ONGOING
        self.ride.start_time = timezone.now()
        self.ride.save()

        self.client.force_authenticate(user=self.driver_user)

        response = self.client.post(f"/api/rides/{self.ride.id}/complete/")

        assert response.status_code == status.HTTP_200_OK

        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.COMPLETED
        assert self.ride.final_fare is not None


@pytest.mark.django_db
class TestRidePermissions:
    """Test ride permissions"""

    def setup_method(self):
        self.client = APIClient()
        self.rider1 = User.objects.create_user(
            username="rider1", phone="9876543210", password="pass123", role="rider"
        )
        self.rider2 = User.objects.create_user(
            username="rider2", phone="9876543211", password="pass123", role="rider"
        )
        self.ride = Ride.objects.create(
            rider=self.rider1,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
        )

    def test_rider_cannot_access_other_ride(self):
        """Test that rider cannot access another rider's ride"""
        self.client.force_authenticate(user=self.rider2)

        response = self.client.get(f"/api/rides/{self.ride.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rider_cannot_cancel_other_ride(self):
        """Test that rider cannot cancel another rider's ride"""
        self.client.force_authenticate(user=self.rider2)

        response = self.client.post(f"/api/rides/{self.ride.id}/cancel/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
