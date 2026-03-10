from decimal import Decimal
from unittest.mock import MagicMock, patch, ANY
import pytest
from apps.rides.services.complete_ride import complete_ride

@pytest.fixture
def mock_ride():
    ride = MagicMock()
    ride.id = 456
    ride.status = "ONGOING"
    ride.Status.ONGOING = "ONGOING"
    ride.Status.COMPLETED = "COMPLETED"
    ride.waiting_seconds = 10
    ride.driver = MagicMock()
    ride.driver_id = 1
    ride.rider = MagicMock()
    return ride

@patch("apps.rides.services.complete_ride.Ride.objects")
@patch("apps.rides.services.complete_ride.persist_ride_history_to_db")
@patch("apps.rides.services.waiting_detector.get_total_waiting_seconds")
@patch("apps.rides.services.waiting_detector.clear_waiting_state")
@patch("apps.rides.services.final_fare.calculate_final_fare")
@patch("apps.rides.services.final_fare.get_fare_breakdown")
@patch("apps.common.fraud.run_fraud_checks")
@patch("apps.rides.services.lifecycle.update_ride_status")
@patch("apps.drivers.services.metrics.update_driver_metrics")
@patch("apps.drivers.services.abuse_detector.check_fake_ride")
@patch("apps.driver_incentives.services.apply_driver_incentive")
@patch("apps.offers.services.offer_engine.OfferEngine.finalize_usage")
def test_complete_ride_success(
    mock_finalize, 
    mock_incentive,
    mock_fake_ride,
    mock_metrics, 
    mock_update_status, 
    mock_fraud,
    mock_breakdown,
    mock_calc_fare,
    mock_clear_waiting,
    mock_waiting, 
    mock_persist, 
    mock_ride_objects, 
    mock_ride
):
    # Setup Ride.objects mock chain
    mock_ride_objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_ride
    
    mock_waiting.return_value = 60 # 1 minute waiting
    mock_calc_fare.return_value = Decimal("150.00")
    mock_breakdown.return_value = {"base": 50}
    mock_fraud.return_value = [] # No fraud
    
    result = complete_ride(456)
    
    # 1. Verify history persistence
    mock_persist.assert_called_once_with(456)
    
    # 2. Verify waiting update (60 > 10)
    assert mock_ride.waiting_seconds == 60
    
    # 3. Verify fare calculation
    assert mock_ride.final_fare == Decimal("150.00")
    
    # 4. Verify status transition
    mock_update_status.assert_called_once_with(mock_ride, "COMPLETED")
    
    # 5. Verify driver metrics
    mock_metrics.assert_called_once_with(mock_ride.driver, "COMPLETED")
    
    # 6. Verify offer finalization
    mock_finalize.assert_called_once_with(mock_ride)
    
    assert result == mock_ride

@patch("apps.rides.services.complete_ride.Ride.objects")
def test_complete_ride_already_completed(mock_ride_objects, mock_ride):
    mock_ride.status = "COMPLETED"
    mock_ride_objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_ride
    
    result = complete_ride(456)
    
    # Should return immediately
    assert result == mock_ride
    # Shouldn't try to update status again (in a real run, other mocks would be here, but let's keep it simple)
