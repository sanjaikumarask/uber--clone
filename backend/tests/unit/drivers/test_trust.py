from unittest.mock import patch, MagicMock
from datetime import timedelta
from apps.drivers.services.trust import register_completed_ride, register_driver_cancellation, register_no_show

@patch("apps.drivers.services.trust.DriverStats")
@patch("apps.drivers.services.trust.transaction.atomic")
def test_register_completed_ride(mock_atomic, mock_Stats_cls):
    # Setup
    mock_stats = MagicMock()
    mock_stats.total_rides = 10
    mock_stats.completed_rides = 8
    mock_Stats_cls.objects.select_for_update.return_value.get_or_create.return_value = (mock_stats, False)

    driver = MagicMock()
    
    register_completed_ride(driver)
    
    assert mock_stats.total_rides == 11
    assert mock_stats.completed_rides == 9
    # Should update specific fields
    mock_stats.save.assert_called()

@patch("apps.drivers.services.trust.DriverStats")
@patch("apps.drivers.services.trust.transaction.atomic")
def test_register_driver_cancellation_penalty(mock_atomic, mock_Stats_cls):
    # Triggers penalty
    mock_stats = MagicMock()
    mock_stats.total_rides = 9
    mock_stats.cancelled_rides = 4 
    # Current: 4/9 = 0.44
    mock_stats.no_shows = 0
    mock_stats.is_suspended = False
    
    mock_Stats_cls.objects.select_for_update.return_value.get_or_create.return_value = (mock_stats, False)
    
    driver = MagicMock()
    
    register_driver_cancellation(driver)
    
    # New Stats: Total 10, Cancelled 5. Rate 0.5 > 0.4.
    assert mock_stats.total_rides == 10
    assert mock_stats.cancelled_rides == 5
    
    # Should be suspended
    assert mock_stats.is_suspended is True
    # suspended_until should be set
    assert mock_stats.suspended_until is not None

@patch("apps.drivers.services.trust.DriverStats")
@patch("apps.drivers.services.trust.transaction.atomic")
def test_register_no_show_penalty(mock_atomic, mock_Stats_cls):
    # Triggers penalty via No Show Count
    mock_stats = MagicMock()
    mock_stats.total_rides = 100
    mock_stats.cancelled_rides = 0
    mock_stats.no_shows = 2 # Suspend at 3
    mock_stats.is_suspended = False
    
    mock_Stats_cls.objects.select_for_update.return_value.get_or_create.return_value = (mock_stats, False)
    
    driver = MagicMock()
    
    register_no_show(driver)
    
    assert mock_stats.no_shows == 3
    assert mock_stats.is_suspended is True
