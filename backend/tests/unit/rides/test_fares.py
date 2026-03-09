from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.rides.services.fare import estimate_fare
from apps.rides.services.final_fare import calculate_final_fare


@patch("apps.rides.services.fare.get_surge")
@patch("apps.rides.services.fare.FareConfig")
@patch("apps.rides.services.fare.get_distance_and_duration")
def test_estimate_fare_success(mock_geo, mock_fare_config_cls, mock_surge):
    # Setup Config
    mock_config = MagicMock()
    mock_config.base_fare = Decimal("50.0")
    mock_config.per_km_rate = Decimal("10.0")
    mock_config.per_min_rate = Decimal("2.0")
    mock_config.minimum_fare = Decimal("60.0")
    mock_config.base_distance_km = Decimal("0.0")
    mock_fare_config_cls.get_for.return_value = mock_config

    # Setup Surge
    mock_surge.return_value = Decimal("1.0")

    # Setup Geo Response (10km, 30min)
    mock_geo.return_value = (10.0, 30.0)

    result = estimate_fare((1, 1), (2, 2))

    # Calculation: (50 + 10x10 + 30x2) * 1.0 = 50 + 100 + 60 = 210
    assert result["estimated_fare"] == Decimal("210.00")
    assert result["distance_km"] == 10.0
    assert result["duration_min"] == 30.0


@patch("apps.rides.services.fare.get_surge")
@patch("apps.rides.services.fare.FareConfig")
@patch("apps.rides.services.fare.get_distance_and_duration")
def test_estimate_fare_fallback(mock_geo, mock_fare_config_cls, mock_surge):
    # Setup Config
    mock_config = MagicMock()
    mock_config.base_fare = Decimal("50.0")
    mock_config.per_km_rate = Decimal("10.0")
    mock_config.per_min_rate = Decimal("2.0")
    mock_config.minimum_fare = Decimal("60.0")
    mock_config.base_distance_km = Decimal("0.0")
    mock_fare_config_cls.get_for.return_value = mock_config

    mock_surge.return_value = Decimal("1.0")

    # Build mocked failure
    mock_geo.side_effect = Exception("Geo Service Down")

    result = estimate_fare((1, 1), (2, 2))

    # Fallback to 5.0 km, 15.0 min
    # Calculation: (50 + 5x10 + 15x2) = 50 + 50 + 30 = 130
    assert result["distance_km"] == 5.0
    assert result["duration_min"] == 15.0
    assert result["estimated_fare"] == Decimal("130.00")


@patch("apps.rides.services.final_fare.get_surge")
@patch("apps.rides.services.final_fare.FareConfig")
def test_calculate_final_fare(mock_fare_config_cls, mock_surge):
    # Setup Config
    mock_config = MagicMock()
    mock_config.base_fare = Decimal("50.0")
    mock_config.per_km_rate = Decimal("10.0")
    mock_config.minimum_fare = Decimal("50.0")
    mock_config.base_distance_km = Decimal("0.0")
    mock_config.waiting_per_minute = Decimal("5.0")
    mock_config.waiting_free_minutes = 2
    mock_fare_config_cls.get_for.return_value = mock_config

    # Surge 1.5
    mock_surge.return_value = Decimal("1.5")

    # Setup Ride
    ride = MagicMock()
    ride.vehicle_type = "go"
    ride.pickup_lat = 13.0
    ride.pickup_lng = 80.0
    ride.actual_distance_km = 10.0
    ride.waiting_seconds = 0
    ride.discount_amount = Decimal("0.00")
    ride.base_fare = None  # Skip shock cap for now

    fare = calculate_final_fare(ride)

    # Calculation: (50 + 10x10 + 0) * 1.5 = 150 * 1.5 = 225.0
    assert fare == Decimal("225.00")


@patch("apps.rides.services.final_fare.get_surge")
@patch("apps.rides.services.final_fare.FareConfig")
def test_calculate_final_fare_minimum(mock_fare_config_cls, mock_surge):
    mock_config = MagicMock()
    mock_config.base_fare = Decimal("10.0")
    mock_config.per_km_rate = Decimal("1.0")
    mock_config.minimum_fare = Decimal("100.0")
    mock_config.base_distance_km = Decimal("0.0")
    mock_config.waiting_per_minute = Decimal("1.0")
    mock_config.waiting_free_minutes = 5
    mock_fare_config_cls.get_for.return_value = mock_config

    mock_surge.return_value = Decimal("1.0")

    # Setup Ride
    ride = MagicMock()
    ride.vehicle_type = "go"
    ride.pickup_lat = 13.0
    ride.pickup_lng = 80.0
    ride.actual_distance_km = 1.0
    ride.waiting_seconds = 0
    ride.discount_amount = Decimal("0.00")
    ride.base_fare = None

    fare = calculate_final_fare(ride)

    # Calculation: (10 + 1x1 + 0) * 1.0 = 11.0
    # Minimum is 100.0
    assert fare == Decimal("100.00")
