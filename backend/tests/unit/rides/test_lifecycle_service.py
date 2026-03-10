import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, ANY
from django.utils import timezone
from datetime import timedelta

from apps.rides.models import Ride
from apps.drivers.models import Driver, DriverStats
from apps.rides.services.lifecycle import update_ride_status

@pytest.mark.django_db
class TestRideLifecycleService:

    @pytest.fixture
    def ride(self, user, driver_user):
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
                status=Ride.Status.SEARCHING,
                base_fare=Decimal("150.00"),
                vehicle_type="SEDAN",
                city="Chennai"
            )

    @patch("apps.rides.services.lifecycle.get_channel_layer")
    @patch("apps.rides.services.lifecycle.async_to_sync")
    @patch("apps.rides.services.lifecycle.generate_and_attach_otp")
    def test_update_status_to_assigned(self, mock_otp, mock_async, mock_channel, ride):
        def side_effect(r):
            r.otp_code = "1234"
            return "1234"
        mock_otp.side_effect = side_effect
        
        update_ride_status(ride, Ride.Status.ASSIGNED)
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED
        assert ride.otp_code == "1234"
        mock_otp.assert_called_once_with(ride)

    @patch("apps.rides.services.lifecycle.get_channel_layer")
    @patch("apps.rides.services.lifecycle.async_to_sync")
    def test_update_status_to_arrived(self, mock_async, mock_channel, ride):
        ride.status = Ride.Status.ASSIGNED
        ride.save()
        
        update_ride_status(ride, Ride.Status.ARRIVED)
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ARRIVED
        assert ride.arrived_at is not None

    @patch("apps.rides.services.lifecycle.get_channel_layer")
    @patch("apps.rides.services.lifecycle.async_to_sync")
    def test_update_status_to_ongoing(self, mock_async, mock_channel, ride):
        ride.status = Ride.Status.ARRIVED
        ride.arrived_at = timezone.now() - timedelta(minutes=5)
        ride.save()
        
        update_ride_status(ride, Ride.Status.ONGOING)
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ONGOING
        assert ride.start_time is not None
        assert ride.otp_verified_at is not None
        assert ride.waiting_seconds >= 300

    @patch("apps.rides.services.lifecycle.get_channel_layer")
    @patch("apps.rides.services.lifecycle.async_to_sync")
    def test_update_status_to_completed(self, mock_async, mock_channel, ride):
        ride.status = Ride.Status.ONGOING
        ride.final_fare = Decimal("200.00")
        ride.save()
        
        driver = ride.driver
        driver.status = Driver.Status.BUSY
        driver.save()
        
        update_ride_status(ride, Ride.Status.COMPLETED)
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.COMPLETED
        assert ride.completed_at is not None
        
        driver.refresh_from_db()
        assert driver.status == Driver.Status.ONLINE
        
        stats = DriverStats.objects.get(driver=driver)
        assert stats.completed_rides == 1
        
        from apps.payments.models import DriverEarnings, Payment
        assert DriverEarnings.objects.filter(ride=ride).exists()
        assert Payment.objects.filter(ride_id=ride.id).exists()

    @patch("apps.rides.services.lifecycle.get_channel_layer")
    @patch("apps.rides.services.lifecycle.async_to_sync")
    def test_update_status_to_cancelled(self, mock_async, mock_channel, ride):
        ride.status = Ride.Status.ASSIGNED
        ride.save()
        
        driver = ride.driver
        driver.status = Driver.Status.BUSY
        driver.save()
        
        update_ride_status(ride, Ride.Status.CANCELLED)
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.CANCELLED
        
        driver.refresh_from_db()
        assert driver.status == Driver.Status.ONLINE

    def test_invalid_transition(self, ride):
        # SEARCHING to COMPLETED is invalid (usually needs ONGOING)
        with pytest.raises(Exception):
            update_ride_status(ride, Ride.Status.COMPLETED)
