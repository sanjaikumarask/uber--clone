from unittest.mock import MagicMock

import pytest

from apps.rides.models import Ride
from apps.tracking.services import LocationProcessor


@pytest.mark.django_db
class TestLocationProcessor:
    """Tests for the LocationProcessor service."""

    def test_filter_noisy_ping(self):
        """Verify that accuracy threshold is correctly enforced."""
        assert LocationProcessor.filter_noisy_ping(150) is True
        assert LocationProcessor.filter_noisy_ping(50) is False
        assert LocationProcessor.filter_noisy_ping(None) is False

    def test_detect_fraud_velocity(self):
        """Verify that unrealistic speed triggers fraud flagging."""
        ride = MagicMock(spec=Ride)
        ride.id = 1
        ride.is_fraud_flagged = False

        # 20km in 10 seconds = 7200 km/h
        is_teleport = LocationProcessor.detect_fraud(ride, 20.0, 10.0)

        assert ride.is_fraud_flagged is True
        assert is_teleport is True
        ride.save.assert_called_with(update_fields=["is_fraud_flagged"])

    def test_detect_normal_velocity(self):
        """Verify that normal speed does NOT trigger fraud flagging."""
        ride = MagicMock(spec=Ride)
        ride.id = 1
        ride.is_fraud_flagged = False

        # 0.1km in 10 seconds = 36 km/h
        is_teleport = LocationProcessor.detect_fraud(ride, 0.1, 10.0)

        assert ride.is_fraud_flagged is False
        assert is_teleport is False
        assert not ride.save.called

    def test_calculate_eta(self, sample_ride):
        """Verify ETA calculation based on haversine distance."""
        # Set status to ASSIGNED to test distance to PICKUP
        sample_ride.status = Ride.Status.ASSIGNED
        sample_ride.save()

        # Near same point
        eta = LocationProcessor.calculate_eta(
            sample_ride, sample_ride.pickup_lat, sample_ride.pickup_lng
        )
        assert eta == 1  # Minimum 1 minute

        # Far from pickup
        # 13.0827, 80.2707 -> pickup
        # 13.0, 80.0 is about 30km away
        eta_far = LocationProcessor.calculate_eta(sample_ride, 13.0, 80.0)
        assert eta_far > 1
