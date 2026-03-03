import pytest
from unittest.mock import patch, MagicMock
from apps.rides.tasks import driver_accept_timeout
from apps.rides.models import Ride
from apps.drivers.models import Driver

@pytest.mark.django_db(transaction=True)
class TestCeleryTasks:

    @patch('apps.notifications.models.Notification.objects.create')
    def test_driver_accept_timeout_logic(self, mock_notify, sample_ride, setup_driver):
        """
        Test that if a driver does not accept in time:
        1. Ride status returns to SEARCHING
        2. Driver is removed from the ride instance
        3. Matching service is re-invoked
        """
        # Set ride to OFFERED
        sample_ride.status = Ride.Status.OFFERED
        sample_ride.driver = setup_driver
        sample_ride.save()
        
        # We need to mock the recursive find_driver_and_offer_ride to prevent infinite loop
        with patch('apps.rides.services.matching.find_driver_and_offer_ride') as mock_match:
            
            # Execute the task manually
            driver_accept_timeout(sample_ride.id, setup_driver.id)
            
            sample_ride.refresh_from_db()
            
            # 1. Assert Status reverted
            assert sample_ride.status == Ride.Status.SEARCHING
            
            # 2. Driver unassigned
            assert sample_ride.driver is None
            
            # 3. Next match search triggered
            mock_match.assert_called_with(sample_ride.id)
            
            # 4. Driver's rejected list updated (to avoid immediate re-offering)
            assert setup_driver.id in sample_ride.rejected_driver_ids

    @pytest.fixture
    def setup_driver(self, db, driver_user):
        driver = Driver.objects.get(user=driver_user)
        driver.is_verified = True
        driver.save()
        return driver
