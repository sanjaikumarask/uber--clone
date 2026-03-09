import pytest
from unittest.mock import patch, MagicMock
from apps.rides.services.matching import find_driver_and_offer_ride, _publish_kafka_match_event
from apps.rides.models import Ride
from apps.drivers.models import Driver, DriverStats
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestMatchingCoverageBoost:
    def setup_method(self, method):
        name = method.__name__
        self.rider = User.objects.create_user(username=f"{name}_rider", role="rider")
        self.driver_user = User.objects.create_user(username=f"{name}_driver", role="driver")
        self.driver, _ = Driver.objects.get_or_create(user=self.driver_user)
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        self.ride = Ride.objects.create(
            rider=self.rider, status=Ride.Status.SEARCHING,
            pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.1, drop_lng=80.1,
            city="Chennai", vehicle_type="go", base_fare=100
        )

    @patch("apps.rides.services.matching.logger")
    def test_publish_kafka_match_event_error_path(self, mock_logger):
        # Trigger line 209-210
        with patch("apps.rides.kafka.publish_ride_match_event", side_effect=Exception("Kafka down")):
            _publish_kafka_match_event(self.ride, [1, 2])
            mock_logger.warning.assert_called_with("Kafka stream error: Kafka down")

    def test_find_driver_and_offer_ride_invalid_status(self):
        # Trigger line 226
        self.ride.status = Ride.Status.COMPLETED
        self.ride.save()
        
        result = find_driver_and_offer_ride(self.ride.id)
        assert result is None # Function returns early

    @patch("apps.rides.services.matching.get_nearby_driver_ids")
    @patch("apps.drivers.services.geo.is_driver_locked", return_value=False)
    @patch("apps.drivers.services.geo.lock_driver_for_offer", return_value=True)
    @patch("apps.drivers.services.metrics.update_driver_metrics")
    @patch("apps.rides.services.matching._notify_match_event")
    def test_find_driver_auto_assign_path(self, mock_notify, mock_metrics, mock_lock, mock_is_locked, mock_nearby):
        # Trigger line 254 (auto_assign = True)
        mock_nearby.return_value = [self.driver.id]
        
        # Set stats to trigger auto-assign (rejection_count_today >= 3)
        from django.utils import timezone
        stats, _ = DriverStats.objects.get_or_create(driver=self.driver)
        stats.rejection_count_today = 3
        stats.last_rejection_date = timezone.now().date()
        stats.save()
        
        find_driver_and_offer_ride(self.ride.id)
        
        # Check if update_driver_metrics(driver, "ACCEPTED") was called (line 254)
        # It's called twice: once for "OFFERED" at line 245, then "ACCEPTED" at 254
        metrics_calls = [call.args[1] for call in mock_metrics.call_args_list]
        assert "ACCEPTED" in metrics_calls
        
        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.ASSIGNED

    @patch("apps.rides.services.matching.get_nearby_driver_ids")
    def test_find_driver_no_drivers_found(self, mock_nearby):
        # Trigger line 238-239
        mock_nearby.return_value = []
        
        find_driver_and_offer_ride(self.ride.id)
        
        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.SEARCHING

    @patch("apps.rides.services.matching.get_nearby_driver_ids")
    @patch("apps.drivers.services.geo.is_driver_locked", return_value=True)
    def test_find_driver_all_locked(self, mock_locked, mock_nearby):
        # Trigger line 237-239 (locking check)
        mock_nearby.return_value = [self.driver.id]
        
        find_driver_and_offer_ride(self.ride.id)
        
        self.ride.refresh_from_db()
        assert self.ride.status == Ride.Status.SEARCHING
