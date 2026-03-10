from decimal import Decimal
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.driver_incentives.models import (
    DriverIncentive,
    DriverIncentiveEarning,
    DriverIncentiveProgress,
)
from apps.driver_incentives.services.incentive_engine import IncentiveEngine
from apps.payments.models import LedgerEntry
from apps.rides.models import Ride

@pytest.mark.django_db
class TestIncentiveEngine:

    @pytest.fixture
    def active_incentive(self):
        return DriverIncentive.objects.create(
            title="Test Streak",
            type=DriverIncentive.Type.STREAK,
            reward_amount=Decimal("50.00"),
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=1),
            is_active=True,
            condition={"rides_required": 3},
            max_per_day=5
        )

    @pytest.fixture
    def real_ride(self, driver_user, user):
        from apps.rides.models import Ride
        # Disabling signals to prevent side effects in unit tests
        with patch("apps.rides.signals.ride_update_signal"):
            return Ride.objects.create(
                rider=user,
                driver=driver_user.driver,
                pickup_lat=12.97,
                pickup_lng=77.59,
                drop_lat=12.98,
                drop_lng=77.60,
                status=Ride.Status.COMPLETED,
                actual_distance_km=Decimal("2.5"),
                start_time=timezone.now() - timedelta(minutes=15),
                end_time=timezone.now(),
                city="Chennai"
            )

    def test_is_valid_ride_for_incentive(self, real_ride):
        assert IncentiveEngine._is_valid_ride_for_incentive(real_ride) is True

        # Too short distance
        real_ride.actual_distance_km = 0.4
        assert IncentiveEngine._is_valid_ride_for_incentive(real_ride) is False
        real_ride.actual_distance_km = 1.0

        # Too short duration
        real_ride.end_time = real_ride.start_time + timedelta(seconds=60)
        assert IncentiveEngine._is_valid_ride_for_incentive(real_ride) is False
        real_ride.end_time = real_ride.start_time + timedelta(minutes=10)

        # Self-ride
        real_ride.rider = real_ride.driver.user
        assert IncentiveEngine._is_valid_ride_for_incentive(real_ride) is False

    @patch("apps.driver_incentives.services.incentive_engine.redis_client")
    def test_handle_streak(self, mock_redis, active_incentive, real_ride):
        driver = real_ride.driver
        
        # Ride 1
        mock_redis.incr.return_value = 1
        IncentiveEngine._handle_streak(driver, active_incentive, real_ride)
        progress = DriverIncentiveProgress.objects.get(driver=driver, incentive=active_incentive)
        assert progress.current_count == 1
        assert not DriverIncentiveEarning.objects.exists()

        # Ride 3 (Completion)
        mock_redis.incr.return_value = 3
        IncentiveEngine._handle_streak(driver, active_incentive, real_ride)
        
        progress.refresh_from_db()
        assert progress.current_count == 0
        assert DriverIncentiveEarning.objects.filter(driver=driver, incentive=active_incentive).exists()
        assert LedgerEntry.objects.filter(user=driver.user, reason=LedgerEntry.Reason.INCENTIVE).exists()

    def test_handle_peak(self, active_incentive, real_ride):
        active_incentive.type = DriverIncentive.Type.PEAK
        active_incentive.condition = {"start_hour": 0, "end_hour": 24} # Always peak for test
        active_incentive.save()

        IncentiveEngine._handle_peak(real_ride.driver, active_incentive, real_ride)
        assert DriverIncentiveEarning.objects.count() == 1

    def test_handle_zone_city(self, active_incentive, real_ride):
        active_incentive.type = DriverIncentive.Type.ZONE
        active_incentive.condition = {"city": "Chennai"}
        active_incentive.save()

        IncentiveEngine._handle_zone(real_ride.driver, active_incentive, real_ride)
        assert DriverIncentiveEarning.objects.count() == 1

    def test_handle_zone_bbox(self, active_incentive, real_ride):
        active_incentive.type = DriverIncentive.Type.ZONE
        active_incentive.condition = {
            "lat_min": 12.0, "lat_max": 13.0,
            "lng_min": 77.0, "lng_max": 78.0
        }
        active_incentive.save()
        
        real_ride.start_lat = 12.5 # Note: In model it may be pickup_lat
        real_ride.pickup_lat = 12.5
        real_ride.pickup_lng = 77.5
        real_ride.save()

        # Mocking getattr because real model might use start_lat or pickup_lat
        with patch.object(real_ride, 'start_lat', 12.5, create=True), \
             patch.object(real_ride, 'start_lng', 77.5, create=True):
            IncentiveEngine._handle_zone(real_ride.driver, active_incentive, real_ride)
        
        assert DriverIncentiveEarning.objects.count() == 1

    def test_process_ride_completion_integration(self, active_incentive, real_ride):
        with patch("apps.driver_incentives.services.incentive_engine.redis_client") as mock_redis:
            mock_redis.incr.return_value = 3
            IncentiveEngine.process_ride_completion(real_ride)
            
            assert DriverIncentiveEarning.objects.filter(ride=real_ride).exists()

    def test_credit_incentive_limits(self, active_incentive, real_ride, user):
        active_incentive.max_per_day = 1
        active_incentive.save()

        # First credit
        IncentiveEngine._credit_incentive(real_ride.driver, active_incentive, real_ride, "First")
        assert DriverIncentiveEarning.objects.count() == 1

        # Second credit same day (different ride)
        with patch("apps.rides.signals.ride_update_signal"):
            ride2 = Ride.objects.create(
                rider=user,
                driver=real_ride.driver,
                pickup_lat=12.97,
                pickup_lng=77.59,
                drop_lat=12.98,
                drop_lng=77.60,
                status=Ride.Status.COMPLETED,
                actual_distance_km=Decimal("2.5"),
                start_time=timezone.now() - timedelta(minutes=15),
                end_time=timezone.now(),
                city="Chennai"
            )
        IncentiveEngine._credit_incentive(real_ride.driver, active_incentive, ride2, "Second")
        assert DriverIncentiveEarning.objects.count() == 1 # Still 1

    def test_credit_incentive_idempotency(self, active_incentive, real_ride):
        # Same ride, same incentive
        IncentiveEngine._credit_incentive(real_ride.driver, active_incentive, real_ride, "Once")
        IncentiveEngine._credit_incentive(real_ride.driver, active_incentive, real_ride, "Twice")
        assert DriverIncentiveEarning.objects.count() == 1
