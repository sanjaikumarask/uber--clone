from unittest.mock import MagicMock, patch
import pytest

# We import the function under test
from apps.rides.services.matching import find_driver_and_offer_ride

# We define the patches as strings to avoid importing Models if possible, 
# but patching where they are USED is key.
# apps.rides.services.matching.Ride

@patch("apps.rides.services.matching.get_nearby_driver_ids")
@patch("apps.rides.services.matching.Ride")
@patch("apps.rides.services.matching.Driver")
@patch("apps.rides.services.matching.transaction.atomic")
def test_matching_logic_success(mock_atomic, mock_Driver_cls, mock_Ride_cls, mock_geo):
    # Setup Constants on Mock
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"
    mock_Ride_cls.Status.OFFERED = "OFFERED"
    mock_Driver_cls.Status.ONLINE = "ONLINE"

    # Setup Mocks
    mock_ride = MagicMock()
    mock_ride.id = 1
    mock_ride.pickup_lat = 10.0
    mock_ride.pickup_lng = 20.0
    mock_ride.status = "SEARCHING"
    mock_ride.rejected_driver_ids = []

    # Mock Ride Query: Ride.objects.select_for_update().filter().first()
    # Ensure chain returns mock_ride
    mock_Ride_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = mock_ride

    # Mock Geo: returns driver IDs
    mock_geo.return_value = [101, 102]

    # Mock Driver Query
    mock_driver = MagicMock()
    mock_driver.id = 101
    mock_Driver_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = mock_driver

    # Call Function
    find_driver_and_offer_ride(1)

    # Assertions
    # We verify save was called (implying success path taken)
    mock_ride.save.assert_called_once()
    
    # We assigned driver to ride
    assert mock_ride.driver == mock_driver
    assert mock_ride.status == "OFFERED"
    
    # We checked nearby drivers
    mock_geo.assert_called_once_with(lat=10.0, lng=20.0, radius_km=5.0, limit=10)

@patch("apps.rides.services.matching.get_nearby_driver_ids")
@patch("apps.rides.services.matching.Ride")
@patch("apps.rides.services.matching.Driver")
@patch("apps.rides.services.matching.transaction.atomic")
def test_matching_no_drivers_found(mock_atomic, mock_Driver_cls, mock_Ride_cls, mock_geo):
    # Setup Constants
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"

    # Setup
    mock_ride = MagicMock()
    mock_ride.status = "SEARCHING"
    mock_ride.pickup_lat = 10.0
    mock_ride.pickup_lng = 20.0
    mock_ride.rejected_driver_ids = []
    
    mock_Ride_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = mock_ride
    
    # Mock Geo returns empty list
    mock_geo.return_value = [] 

    # Call
    find_driver_and_offer_ride(1)

    # Assert
    # Save should NOT be called (status remains SEARCHING)
    mock_ride.save.assert_not_called()

@patch("apps.rides.services.matching.get_nearby_driver_ids")
@patch("apps.rides.services.matching.Ride")
@patch("apps.rides.services.matching.Driver")
@patch("apps.rides.services.matching.transaction.atomic")
def test_matching_skip_rejected_drivers(mock_atomic, mock_Driver_cls, mock_Ride_cls, mock_geo):
    # Setup Constants
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"
    mock_Ride_cls.Status.OFFERED = "OFFERED"
    mock_Driver_cls.Status.ONLINE = "ONLINE"

    # Setup
    mock_ride = MagicMock()
    mock_ride.status = "SEARCHING"
    mock_ride.pickup_lat = 10.0
    mock_ride.pickup_lng = 20.0
    # Driver 101 already rejected this ride
    mock_ride.rejected_driver_ids = [101]
    
    mock_Ride_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = mock_ride
    
    # Geo returns 101 and 102
    mock_geo.return_value = [101, 102]

    # Mock Driver 102 (should be picked)
    mock_driver_102 = MagicMock()
    mock_driver_102.id = 102
    
    # Configure Driver query to return mock_driver_102
    mock_Driver_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = mock_driver_102

    # Call
    find_driver_and_offer_ride(1)

    # Assert
    # Verify filter called with correct ID
    # We check the arguments passed to filter()
    # Driver.objects.select_for_update().filter(id=..., ...)
    filter_mock = mock_Driver_cls.objects.select_for_update.return_value.filter
    
    assert filter_mock.call_count >= 1, "Driver filter query was not called"
    
    call_args = filter_mock.call_args
    # call_args is (args, kwargs)
    assert call_args[1]['id'] == 102 # Selected ID should be 102
    
    assert mock_ride.driver == mock_driver_102
