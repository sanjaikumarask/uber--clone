import pytest
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.rides.services.otp import generate_and_attach_otp


@pytest.mark.django_db
class TestRideEndToEnd:

    @patch("apps.rides.views.get_planned_route")
    def test_full_ride_lifecycle(self, mock_get_route):

        mock_get_route.return_value = {
            "polyline": "mock_polyline",
            "distance_km": 5.2,
            "duration_min": 14,
        }

        client = APIClient()

        rider = User.objects.create_user(
            username="rider1",
            password="pass12345",
            role=User.ROLE_RIDER,
        )

        driver_user = User.objects.create_user(
            username="driver1",
            password="pass12345",
            role=User.ROLE_DRIVER,
        )

        driver = Driver.objects.get(user=driver_user)

        client.force_authenticate(user=rider)

        # ===============================
        # CREATE RIDE
        # ===============================
        res = client.post(
            "/api/rides/create/",
            {
                "pickup_lat": 12.9716,
                "pickup_lng": 77.5946,
                "drop_lat": 12.9352,
                "drop_lng": 77.6245,
            },
            format="json",
        )

        assert res.status_code == 201

        ride = Ride.objects.get(id=res.data["ride_id"])
        assert ride.status == Ride.Status.SEARCHING

        # ===============================
        # SIMULATE MATCH
        # ===============================
        ride.driver = driver
        ride.status = Ride.Status.ASSIGNED
        ride.save(update_fields=["driver", "status"])

        # ===============================
        # DRIVER ARRIVES → GENERATE OTP
        # ===============================
        ride.status = Ride.Status.ARRIVED
        ride.arrived_at = ride.created_at
        ride.save(update_fields=["status", "arrived_at"])

        otp = generate_and_attach_otp(ride)

        # ===============================
        # RIDER VERIFIES OTP
        # ===============================
        res = client.post(
            f"/api/rides/{ride.id}/verify-otp/",
            {"otp": otp},
            format="json",
        )

        assert res.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.ONGOING
        assert ride.otp_verified_at is not None

        # ===============================
        # COMPLETE RIDE
        # ===============================
        client.force_authenticate(user=driver_user)

        res = client.post(
            f"/api/rides/{ride.id}/complete/",
            format="json",
        )

        assert res.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.COMPLETED
        assert ride.final_fare is not None
