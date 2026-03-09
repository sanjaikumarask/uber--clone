import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.utils import timezone
from decimal import Decimal

from apps.common.fraud import (
    detect_ghost_ride,
    detect_route_inflation,
    detect_frequency_anomaly,
    detect_coordinated_abuse,
    validate_gps_velocity,
    run_fraud_checks,
    apply_fraud_penalties
)
from apps.rides.models import Ride
from apps.drivers.models import Driver

@pytest.mark.django_db
class TestFraudDetection:

    def test_detect_ghost_ride(self):
        ride = MagicMock()
        ride.start_time = timezone.now()
        ride.completed_at = ride.start_time + timedelta(seconds=30)
        assert detect_ghost_ride(ride) is True

        ride.completed_at = ride.start_time + timedelta(seconds=100)
        assert detect_ghost_ride(ride) is False

    def test_detect_route_inflation(self):
        ride = MagicMock()
        ride.actual_distance_km = 10.0
        ride.planned_distance_km = 4.0 # 2.5x > 2.0x
        assert detect_route_inflation(ride) is True

        ride.actual_distance_km = 5.0
        ride.planned_distance_km = 4.0 # 1.25x
        assert detect_route_inflation(ride) is False

    def test_detect_frequency_anomaly(self, driver_user):
        driver = driver_user.driver
        # Create 7 rides in the last hour
        for i in range(7):
            with patch("apps.rides.signals.ride_update_signal"):
                Ride.objects.create(
                    driver=driver,
                    rider=driver_user, # irrelevant for this test
                    status=Ride.Status.COMPLETED,
                    completed_at=timezone.now() - timedelta(minutes=5),
                    pickup_lat=12.97, pickup_lng=77.59,
                    drop_lat=12.98, drop_lng=77.60
                )
        
        assert detect_frequency_anomaly(driver) is True

    def test_detect_coordinated_abuse(self, driver_user, user):
        driver = driver_user.driver
        # Create 3 rides with same rider-driver pair in 24h
        for i in range(3):
            with patch("apps.rides.signals.ride_update_signal"):
                Ride.objects.create(
                    driver=driver,
                    rider=user,
                    status=Ride.Status.COMPLETED,
                    completed_at=timezone.now() - timedelta(hours=2),
                    pickup_lat=12.97, pickup_lng=77.59,
                    drop_lat=12.98, drop_lng=77.60
                )
        
        ride = MagicMock()
        ride.rider = user
        assert detect_coordinated_abuse(driver, ride) is True

    @patch("apps.drivers.redis.redis_client")
    def test_validate_gps_velocity_teleport(self, mock_redis):
        driver_id = 1
        # Mock last seen at (12.97, 77.59) 10 seconds ago
        import time
        now = int(time.time())
        mock_redis.hgetall.return_value = {
            "lat": "12.97",
            "lng": "77.59",
            "last_seen": str(now - 10)
        }
        
        # New location: New York (approx 12000 km away)
        # This is definitely > 150 km/h
        assert validate_gps_velocity(driver_id, 40.7128, -74.0060) is False
        mock_redis.hincrby.assert_called_with(f"driver:{driver_id}:fraud", "spoof_count", 1)

    @patch("apps.drivers.redis.redis_client")
    def test_validate_gps_velocity_normal(self, mock_redis):
        driver_id = 2
        import time
        now = int(time.time())
        mock_redis.hgetall.return_value = {
            "lat": "12.9716",
            "lng": "77.5946",
            "last_seen": str(now - 60)
        }
        
        # New location: 500 meters away
        assert validate_gps_velocity(driver_id, 12.9750, 77.5946) is True
        mock_redis.hset.assert_called()

    def test_run_fraud_checks_composite(self, driver_user, user):
        driver = driver_user.driver
        ride = MagicMock()
        ride.driver = driver
        ride.rider = user
        ride.start_time = timezone.now()
        ride.completed_at = ride.start_time + timedelta(seconds=30) # Ghost ride
        
        with patch("apps.common.fraud.detect_frequency_anomaly", return_value=False):
            with patch("apps.common.fraud.detect_coordinated_abuse", return_value=False):
                with patch("apps.common.fraud.detect_route_inflation", return_value=True):
                    signals = run_fraud_checks(ride)
                    assert "GHOST_RIDE" in signals
                    assert "ROUTE_INFLATION" in signals

    def test_apply_fraud_penalties(self, driver_user):
        driver = driver_user.driver
        from apps.drivers.models import DriverStats
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        stats.trust_score = 100.0
        stats.save()
        
        ride = MagicMock()
        ride.driver = driver
        ride.driver_id = driver.id
        ride.id = 999
        
        with patch("apps.notifications.services.alerts.send_critical_alert") as mock_alert:
            apply_fraud_penalties(ride, ["GHOST_RIDE", "ROUTE_INFLATION"])
            
            stats.refresh_from_db()
            # Penalty: 10 + 8 = 18
            assert stats.trust_score == 82.0
            assert stats.fraud_flags_count == 1
            mock_alert.assert_called_once()

    def test_apply_fraud_penalties_suspension(self, driver_user):
        driver = driver_user.driver
        from apps.drivers.models import DriverStats
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        stats.trust_score = 35.0
        stats.save()
        
        ride = MagicMock()
        ride.driver = driver
        ride.driver_id = driver.id
        
        with patch("apps.notifications.services.alerts.send_critical_alert"):
            apply_fraud_penalties(ride, ["GHOST_RIDE"]) # -10 penalty
            
            stats.refresh_from_db()
            assert stats.trust_score == 25.0
            driver.refresh_from_db()
            assert driver.status == Driver.Status.BLOCKED
