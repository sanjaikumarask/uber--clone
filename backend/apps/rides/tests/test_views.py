from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from apps.drivers.models import Driver
from apps.rides.models import Ride


@pytest.mark.django_db
class TestRidesAPI:
    """Tests for the DRF views in apps/rides/views.py."""

    def test_estimate_fare_success(self, authenticated_rider_client, mock_google_maps):
        """Verify fare estimation endpoint."""
        url = reverse("ride-estimate")
        data = {
            "pickup_lat": 13.0827,
            "pickup_lng": 80.2707,
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
        }

        response = authenticated_rider_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "estimated_fare" in response.data
        assert "polyline" in response.data

    def test_create_ride_success(self, authenticated_rider_client, mock_google_maps):
        """Verify ride creation endpoint and matchmaking trigger."""
        url = reverse("ride-create")
        data = {
            "pickup_lat": 13.08,
            "pickup_lng": 80.27,
            "drop_lat": 13.05,
            "drop_lng": 80.24,
            "vehicle_type": "go",
        }

        with patch(
            "apps.rides.services.matching.find_driver_and_offer_ride"
        ):
            response = authenticated_rider_client.post(url, data)

            assert response.status_code == status.HTTP_201_CREATED
            ride_id = response.data["id"]
            ride = Ride.objects.get(id=ride_id)
            assert ride.status == Ride.Status.SEARCHING

    def test_accept_ride_success(self, authenticated_driver_client, driver_user):
        """Verify driver acceptance endpoint."""
        driver = Driver.objects.get(user=driver_user)
        driver.status = Driver.Status.ONLINE
        driver.save()

        ride = Ride.objects.create(
            rider=driver_user,
            driver=driver,
            pickup_lat=13.0,
            pickup_lng=80.0,
            drop_lat=13.1,
            drop_lng=80.1,
            status=Ride.Status.OFFERED,
            base_fare=Decimal("100.00"),
        )

        url = reverse("ride-accept", kwargs={"ride_id": ride.id})

        response = authenticated_driver_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED
        driver.refresh_from_db()
        assert driver.status == Driver.Status.BUSY
