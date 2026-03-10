from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.utils import timezone
import pytest
from apps.rides.services.stale_resolver import auto_resolve_stale_rides
from apps.rides.models import Ride

@pytest.fixture
def mock_now():
    return timezone.now()

@patch("apps.rides.services.stale_resolver.timezone")
@patch("apps.rides.services.stale_resolver.Ride.objects.filter")
@patch("apps.rides.services.stale_resolver.cancel_ride")
@patch("apps.rides.services.stale_resolver.complete_ride")
def test_auto_resolve_stale_rides_logic(mock_complete, mock_cancel, mock_filter, mock_tz, mock_now):
    """Test that stale searching rides are cancelled and abandoned ongoing rides are handled."""
    mock_tz.now.return_value = mock_now
    
    # Setup mock rides
    ride_searching = MagicMock(id=1, status="SEARCHING")
    ride_ongoing = MagicMock(id=2, status="ONGOING")
    ride_arrived = MagicMock(id=3, status="ARRIVED")
    
    # Mock filters to act like QuerySets (supporting iterate and count())
    mock_stale = MagicMock()
    mock_stale.__iter__.return_value = [ride_searching]
    mock_stale.count.return_value = 1
    
    mock_abandoned = MagicMock()
    mock_abandoned.__iter__.return_value = [ride_ongoing, ride_arrived]
    mock_abandoned.count.return_value = 2
    
    mock_filter.side_effect = [mock_stale, mock_abandoned]
    
    result = auto_resolve_stale_rides()
    
    # Verify searching ride was cancelled
    mock_cancel.assert_any_call(ride_searching, by="SYSTEM")
    
    # Verify ongoing ride was completed
    mock_complete.assert_called_once_with(ride_ongoing.id)
    
    # Verify arrived ride was cancelled (it's in the abandoned list)
    mock_cancel.assert_any_call(ride_arrived, by="SYSTEM")
    
    assert "Processed 3" in result

@patch("apps.rides.services.stale_resolver.timezone")
@patch("apps.rides.services.stale_resolver.Ride.objects.filter")
@patch("apps.rides.services.stale_resolver.complete_ride")
def test_auto_resolve_handles_exceptions(mock_complete, mock_filter, mock_tz, mock_now):
    """Test that resolver continues even if one ride resolution fails."""
    mock_tz.now.return_value = mock_now
    
    ride_fail = MagicMock(id=99, status="ONGOING")
    
    # Mock empty searching
    m1 = MagicMock()
    m1.__iter__.return_value = []
    m1.count.return_value = 0
    
    # Mock one ongoing
    m2 = MagicMock()
    m2.__iter__.return_value = [ride_fail]
    m2.count.return_value = 1
    
    mock_filter.side_effect = [m1, m2]
    
    mock_complete.side_effect = Exception("Mock complete failed")
    
    # Should not raise exception
    result = auto_resolve_stale_rides()
    assert "Processed 1" in result
    mock_complete.assert_called_once()
