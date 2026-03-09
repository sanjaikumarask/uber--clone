import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils import timezone

from apps.rides.models import Ride
from apps.rides.services.lifecycle import update_ride_status, _handle_completed
from apps.rides.services.cancellation import cancel_ride
from apps.rides.services.surge import get_surge, get_surge_multiplier
from apps.rides.services.matching import find_driver_and_offer_ride

import uuid

@pytest.fixture
def rider_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(
        username=f"rider_cov_{uid}", phone=f"+123456{uid[:4]}", role="rider"
    )

@pytest.fixture
def driver_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(
        username=f"driver_cov_{uid}", phone=f"+198765{uid[:4]}", role="driver"
    )

@pytest.fixture
def driver_profile(driver_user):
    from apps.drivers.models import Driver
    profile, _ = Driver.objects.get_or_create(
        user=driver_user,
        defaults={'status': Driver.Status.ONLINE, 'level': Driver.Level.NORMAL}
    )
    profile.status = Driver.Status.ONLINE
    profile.save()
    return profile

@pytest.fixture
def ride(rider_user):
    return Ride.objects.create(
        rider=rider_user,
        pickup_lat=12.9716,
        pickup_lng=77.5946,
        drop_lat=12.9352,
        drop_lng=77.6245,
        status=Ride.Status.SEARCHING,
    )

@pytest.mark.django_db
class TestTransitionCoverage:
    def test_transition_searching_to_assigned(self, ride, driver_profile):
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            updated_ride = update_ride_status(ride, Ride.Status.ASSIGNED, driver=driver_profile)
        assert updated_ride.status == Ride.Status.ASSIGNED
        assert updated_ride.driver == driver_profile

    def test_transition_searching_to_offered(self, ride, driver_profile):
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            updated_ride = update_ride_status(ride, Ride.Status.OFFERED, driver=driver_profile)
        assert updated_ride.status == Ride.Status.OFFERED

    def test_transition_assigned_to_arrived(self, ride, driver_profile):
        ride.status = Ride.Status.ASSIGNED
        ride.driver = driver_profile
        ride.save()
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            updated_ride = update_ride_status(ride, Ride.Status.ARRIVED)
        assert updated_ride.status == Ride.Status.ARRIVED
        assert updated_ride.arrived_at is not None

    def test_transition_arrived_to_ongoing(self, ride, driver_profile):
        ride.status = Ride.Status.ARRIVED
        ride.driver = driver_profile
        ride.arrived_at = timezone.now()
        ride.save()
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            updated_ride = update_ride_status(ride, Ride.Status.ONGOING)
        assert updated_ride.status == Ride.Status.ONGOING
        assert updated_ride.start_time is not None

    def test_transition_ongoing_to_completed(self, ride, driver_profile):
        ride.status = Ride.Status.ONGOING
        ride.driver = driver_profile
        ride.final_fare = Decimal("150.00")
        ride.save()
        with patch('apps.rides.services.lifecycle._broadcast_status_update'), \
             patch('apps.rides.services.lifecycle._send_completion_notifications'):
            updated_ride = update_ride_status(ride, Ride.Status.COMPLETED)
        assert updated_ride.status == Ride.Status.COMPLETED
        assert updated_ride.completed_at is not None

    def test_transition_invalid(self, ride):
        with pytest.raises(DjangoValidationError):
            update_ride_status(ride, Ride.Status.COMPLETED)

    def test_transition_terminal_completed(self, ride):
        ride.status = Ride.Status.COMPLETED
        ride.save()
        with pytest.raises(DjangoValidationError):
            ride.transition_to(Ride.Status.SEARCHING)

    def test_transition_terminal_cancelled(self, ride):
        ride.status = Ride.Status.CANCELLED
        ride.save()
        with pytest.raises(DjangoValidationError):
            ride.transition_to(Ride.Status.SEARCHING)

@pytest.mark.django_db
class TestCancellationCoverage:
    def test_cancel_searching(self, ride):
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            cancel_ride(ride=ride, by=Ride.CancelledBy.RIDER)
        assert ride.status == Ride.Status.CANCELLED
        assert ride.cancelled_by == Ride.CancelledBy.RIDER

    def test_cancel_assigned_fee(self, ride, driver_profile):
        ride.status = Ride.Status.ASSIGNED
        ride.driver = driver_profile
        ride.save()
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            cancel_ride(ride=ride, by=Ride.CancelledBy.RIDER)
        assert ride.status == Ride.Status.CANCELLED
        
    def test_cancel_arrived_fee(self, ride, driver_profile):
        ride.status = Ride.Status.ARRIVED
        ride.driver = driver_profile
        ride.save()
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            cancel_ride(ride=ride, by=Ride.CancelledBy.RIDER)
        assert ride.status == Ride.Status.CANCELLED

    def test_cancel_by_driver(self, ride, driver_profile):
        ride.status = Ride.Status.ASSIGNED
        ride.driver = driver_profile
        ride.save()
        with patch('apps.rides.services.lifecycle._broadcast_status_update'):
            cancel_ride(ride=ride, by=Ride.CancelledBy.DRIVER)
        assert ride.status == Ride.Status.CANCELLED

    def test_cancel_already_completed(self, ride):
        ride.status = Ride.Status.COMPLETED
        ride.save()
        with pytest.raises(DRFValidationError):
            cancel_ride(ride=ride, by=Ride.CancelledBy.RIDER)


@pytest.mark.django_db
class TestSurgeCoverage:
    @patch('apps.rides.services.surge.redis_client.get')
    def test_get_surge_no_value(self, mock_get):
        mock_get.return_value = None
        assert get_surge(12.9716, 77.5946) == 1.0

    @patch('apps.rides.services.surge.redis_client.get')
    def test_get_surge_with_value(self, mock_get):
        mock_get.return_value = b'1.5'
        assert get_surge(12.9716, 77.5946) == 1.5


@pytest.mark.django_db(transaction=True)
class TestMatchingCoverage:
    @patch('apps.rides.services.matching._get_sorted_candidates')
    def test_find_driver_not_found(self, mock_get_candidates, ride):
        mock_get_candidates.return_value = ([], [])
        # Should gracefully return without modifying ride
        assert find_driver_and_offer_ride(ride.id) is None

    @patch('apps.drivers.services.geo.is_driver_locked')
    @patch('apps.rides.services.matching._get_sorted_candidates')
    def test_find_driver_all_locked(self, mock_get_candidates, mock_is_locked, ride, driver_profile):
        mock_get_candidates.return_value = ([driver_profile], [driver_profile.id])
        mock_is_locked.return_value = True
        
        assert find_driver_and_offer_ride(ride.id) is None

    @patch('apps.drivers.services.geo.lock_driver_for_offer')
    @patch('apps.drivers.services.geo.is_driver_locked')
    @patch('apps.rides.services.matching._get_sorted_candidates')
    def test_find_driver_lock_fails(self, mock_get_candidates, mock_is_locked, mock_lock_driver, ride, driver_profile):
        mock_get_candidates.return_value = ([driver_profile], [driver_profile.id])
        mock_is_locked.return_value = False
        mock_lock_driver.return_value = False # Condition: driver exists BUT not locked
        
        assert find_driver_and_offer_ride(ride.id) is None

    @patch('apps.rides.tasks.driver_accept_timeout.apply_async')
    @patch('apps.drivers.services.metrics.update_driver_metrics')
    @patch('apps.drivers.services.geo.lock_driver_for_offer')
    @patch('apps.drivers.services.geo.is_driver_locked')
    @patch('apps.rides.services.matching._get_sorted_candidates')
    @patch('apps.rides.services.lifecycle._broadcast_status_update')
    def test_find_driver_success_offered(self, mock_broadcast, mock_get_candidates, mock_is_locked, mock_lock_driver, mock_update_metrics, mock_timeout, ride, driver_profile):
        mock_get_candidates.return_value = ([driver_profile], [driver_profile.id])
        mock_is_locked.return_value = False
        mock_lock_driver.return_value = True

        find_driver_and_offer_ride(ride.id)
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.OFFERED
        assert ride.driver == driver_profile
