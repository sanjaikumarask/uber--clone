import pytest
from unittest.mock import MagicMock, patch, ANY
from django.db import transaction
from apps.rides.services.matching import find_driver_and_offer_ride, _get_sorted_candidates
from apps.rides.models import Ride
from apps.drivers.models import Driver

@pytest.mark.django_db(transaction=True)
class TestMatchingService:

    @patch("apps.rides.services.matching.get_nearby_driver_ids")
    def test_get_sorted_candidates(self, mock_nearby, driver_user):
        driver = driver_user.driver
        driver.level = Driver.Level.PRO
        driver.status = Driver.Status.ONLINE
        driver.save()
        
        # Ensure stats exist
        from apps.drivers.models import DriverStats
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        stats.trust_score = 90.0
        stats.save()
        
        ride = MagicMock(spec=Ride)
        ride.pickup_lat = 12.97
        ride.pickup_lng = 77.59
        
        mock_nearby.return_value = [driver.id]
        
        with transaction.atomic():
            candidates, all_ids = _get_sorted_candidates(ride, rejected_ids=[])
        assert len(candidates) == 1
        assert candidates[0].id == driver.id

    @patch("apps.rides.services.matching.get_nearby_driver_ids")
    @patch("apps.drivers.services.geo.lock_driver_for_offer", return_value=True)
    @patch("apps.drivers.services.geo.is_driver_locked", return_value=False)
    @patch("apps.rides.services.matching.update_ride_status")
    def test_find_driver_and_offer_ride_success(self, mock_update, mock_is_locked, mock_lock, mock_nearby, driver_user):
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.save()
        
        ride = Ride.objects.create(
            rider=driver_user, # dummy
            pickup_lat=12.97, pickup_lng=77.59,
            drop_lat=12.98, drop_lng=77.60,
            status=Ride.Status.SEARCHING,
            city="Chennai",
            vehicle_type="go",
            base_fare=100.0
        )
        
        mock_nearby.return_value = [driver.id]
        
        # Need to patch driver_accept_timeout as well since it's called inside
        with patch("apps.rides.services.matching.driver_accept_timeout.apply_async"):
            find_driver_and_offer_ride(ride.id)
            
        ride.refresh_from_db()
        mock_update.assert_called_once()
        # Verify status update was called correctly
        # The actual side effect of update_ride_status should be handled in its own tests,
        # here we just verify the matching service calls it with the right driver.
        call_args = mock_update.call_args[0]
        assert call_args[1] == Ride.Status.OFFERED
        assert mock_update.call_args[1]['driver'] == driver

    @patch("apps.rides.services.matching.get_nearby_driver_ids")
    def test_find_driver_no_candidates(self, mock_nearby, driver_user):
        ride = Ride.objects.create(
            rider=driver_user,
            pickup_lat=12.97, pickup_lng=77.59,
            drop_lat=12.98, drop_lng=77.60,
            status=Ride.Status.SEARCHING
        )
        mock_nearby.return_value = []
        
        with patch("apps.rides.services.matching.logger.info") as mock_log:
            find_driver_and_offer_ride(ride.id)
            mock_log.assert_any_call(f"Ride {ride.id}: No eligible or available drivers.")
