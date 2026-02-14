from unittest.mock import patch, MagicMock
from decimal import Decimal
from apps.rides.services.fare import estimate_fare
from apps.rides.services.final_fare import calculate_final_fare

@patch("apps.rides.services.fare.fare_config")
@patch("apps.rides.services.fare.get_distance_and_duration")
def test_estimate_fare_success(mock_geo, mock_config):
    # Setup Config
    mock_config.BASE_FARE = Decimal("50.0")
    mock_config.PER_KM_RATE = Decimal("10.0")
    mock_config.PER_MIN_RATE = Decimal("2.0")
    mock_config.SURGE_MULTIPLIER = Decimal("1.0")
    mock_config.MINIMUM_FARE = Decimal("60.0")

    # Setup Geo Response (10km, 30min)
    mock_geo.return_value = (10.0, 30.0) 

    result = estimate_fare((1,1), (2,2))

    # Calculation: (50 + 10*10 + 30*2) * 1.0 = 50 + 100 + 60 = 210
    assert result["estimated_fare"] == Decimal("210.00")
    assert result["distance_km"] == 10.0
    assert result["duration_min"] == 30.0

@patch("apps.rides.services.fare.fare_config")
@patch("apps.rides.services.fare.get_distance_and_duration")
def test_estimate_fare_fallback(mock_geo, mock_config):
    # Setup Config
    mock_config.BASE_FARE = Decimal("50.0")
    mock_config.PER_KM_RATE = Decimal("10.0")
    mock_config.PER_MIN_RATE = Decimal("2.0")
    mock_config.SURGE_MULTIPLIER = Decimal("1.0")
    mock_config.MINIMUM_FARE = Decimal("60.0")

    # Build mocked failure
    mock_geo.side_effect = Exception("Geo Service Down")

    result = estimate_fare((1,1), (2,2))

    # Fallback to 5.0 km, 15.0 min
    # Calculation: (50 + 5*10 + 15*2) = 50 + 50 + 30 = 130
    assert result["distance_km"] == 5.0
    assert result["duration_min"] == 15.0
    assert result["estimated_fare"] == Decimal("130.00")

@patch("apps.rides.services.final_fare.get_surge_multiplier")
@patch("apps.rides.services.final_fare.fare_config")
def test_calculate_final_fare(mock_config, mock_surge):
    # Setup Config
    mock_config.PER_KM_RATE = Decimal("10.0")
    mock_config.MINIMUM_FARE = Decimal("50.0")
    
    # Surge 1.5
    mock_surge.return_value = 1.5

    fare = calculate_final_fare(
        base_fare=Decimal("50.0"),
        actual_distance_km=10.0,
        surge_cell_id="cell_123"
    )

    # Calculation: (50 + 10*10) * 1.5 = 150 * 1.5 = 225.0
    assert fare == Decimal("225.00")

@patch("apps.rides.services.final_fare.get_surge_multiplier")
@patch("apps.rides.services.final_fare.fare_config")
def test_calculate_final_fare_minimum(mock_config, mock_surge):
    mock_config.PER_KM_RATE = Decimal("1.0")
    mock_config.MINIMUM_FARE = Decimal("100.0")
    mock_surge.return_value = 1.0

    fare = calculate_final_fare(
        base_fare=Decimal("10.0"),
        actual_distance_km=1.0,
        surge_cell_id="cell_123"
    )

    # Calculation: (10 + 1*1) * 1.0 = 11.0
    # Minimum is 100.0
    assert fare == Decimal("100.00")
