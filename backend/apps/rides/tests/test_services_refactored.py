from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.drivers.models import Driver, DriverStats
from apps.rides.models import Ride
from apps.rides.services.lifecycle import update_ride_status
from apps.rides.services.matching import find_driver_and_offer_ride


@pytest.fixture
def mock_channel_layer():
    with patch("apps.rides.services.matching.channel_layer") as mock_cl:
        mock_cl.group_send = MagicMock()
        # Important: async_to_sync(mock_cl.group_send) will try to await the result
        # So we must make group_send return an awaitable, or use AsyncMock
        from unittest.mock import AsyncMock

        mock_cl.group_send = AsyncMock()
        yield mock_cl


@pytest.fixture
def mock_redis():
    with patch("apps.drivers.redis.redis_client") as mock_r:
        mock_r.get.return_value = None
        mock_r.set.return_value = True
        mock_r.exists.return_value = False
        mock_r.delete.return_value = 1
        # Mock geo property if needed (though we mostly patch the service)
        mock_r.geosearch.return_value = []
        yield mock_r


@pytest.mark.django_db
class TestRideLifecycleService:
    """Tests for the refactored Ride Lifecycle Service."""

    def test_transition_to_assigned(self, sample_ride, driver_user):
        """Verify SEARCHING -> ASSIGNED generates OTP."""
        driver = Driver.objects.get(user=driver_user)
        sample_ride.driver = driver
        sample_ride.save(update_fields=["driver"])

        # Test transition
        update_ride_status(sample_ride, Ride.Status.ASSIGNED)

        sample_ride.refresh_from_db()
        assert sample_ride.status == Ride.Status.ASSIGNED
        assert sample_ride.otp_code is not None
        assert len(sample_ride.otp_code) == 4

    def test_transition_to_arrived(self, assigned_ride):
        """Verify ASSIGNED -> ARRIVED sets arrived_at."""
        update_ride_status(assigned_ride, Ride.Status.ARRIVED)

        assigned_ride.refresh_from_db()
        assert assigned_ride.status == Ride.Status.ARRIVED
        assert assigned_ride.arrived_at is not None

    def test_transition_to_ongoing(self, assigned_ride):
        """Verify ARRIVED -> ONGOING sets start_time and waiting_seconds."""
        assigned_ride.status = Ride.Status.ARRIVED
        assigned_ride.arrived_at = timezone.now() - timezone.timedelta(minutes=5)
        assigned_ride.save()

        update_ride_status(assigned_ride, Ride.Status.ONGOING)

        assigned_ride.refresh_from_db()
        assert assigned_ride.status == Ride.Status.ONGOING
        assert assigned_ride.start_time is not None
        assert assigned_ride.waiting_seconds >= 300  # 5 minutes


@pytest.mark.django_db(transaction=True)
class TestMatchmakingService:
    """Tests for the refactored Matchmaking Service."""

    def test_find_driver_success(
        self, sample_ride, driver_user, mock_channel_layer, mock_redis
    ):
        """Verify successful driver matching and notification."""
        driver = Driver.objects.get(user=driver_user)
        driver.status = Driver.Status.ONLINE
        driver.is_verified = True
        driver.last_lat = sample_ride.pickup_lat
        driver.last_lng = sample_ride.pickup_lng
        driver.save()

        # Ensure stats exist with high trust score
        stats, _ = DriverStats.objects.get_or_create(driver=driver.user)
        stats.trust_score = 100.0
        stats.save()

        with (
            patch("apps.rides.services.matching.get_nearby_driver_ids") as mock_geo,
            patch("apps.rides.services.matching.driver_accept_timeout") as mock_timeout,
        ):
            mock_geo.return_value = [driver.id]

            find_driver_and_offer_ride(sample_ride.id)

            sample_ride.refresh_from_db()
            assert sample_ride.driver == driver
            assert sample_ride.status == Ride.Status.OFFERED
            assert mock_channel_layer.group_send.called
            assert mock_timeout.apply_async.called
