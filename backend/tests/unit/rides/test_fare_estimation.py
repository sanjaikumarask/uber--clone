from unittest.mock import MagicMock, patch
from decimal import Decimal

import pytest


# ─── estimate_fare ────────────────────────────────────────────────────────────

@patch("apps.rides.services.fare.get_surge")
@patch("apps.rides.services.fare.get_distance_and_duration")
@patch("apps.rides.services.fare.FareConfig")
def test_estimate_fare_normal(mock_fare_config, mock_distance, mock_get_surge):
    config = MagicMock()
    config.base_fare = Decimal("50.00")
    config.per_km_rate = Decimal("12.00")
    config.per_min_rate = Decimal("1.00")
    config.base_distance_km = Decimal("2.0")
    config.minimum_fare = Decimal("40.00")
    mock_fare_config.get_for.return_value = config

    mock_distance.return_value = (10.0, 20.0)  # 10km, 20min
    mock_get_surge.return_value = 1.0

    result = _call_estimate_fare((12.97, 77.59), (13.0, 77.6))

    assert "estimated_fare" in result
    assert "distance_km" in result
    assert result["distance_km"] == 10.0
    assert result["surge_multiplier"] == 1.0
    # Base: 50 + (10-2)*12 + 20*1 = 50 + 96 + 20 = 166
    assert result["estimated_fare"] == Decimal("166.00")


@patch("apps.rides.services.fare.get_surge")
@patch("apps.rides.services.fare.get_distance_and_duration")
@patch("apps.rides.services.fare.FareConfig")
def test_estimate_fare_api_failure_uses_fallback(mock_fare_config, mock_distance, mock_get_surge):
    config = MagicMock()
    config.base_fare = Decimal("50.00")
    config.per_km_rate = Decimal("12.00")
    config.per_min_rate = Decimal("1.00")
    config.base_distance_km = Decimal("2.0")
    config.minimum_fare = Decimal("40.00")
    mock_fare_config.get_for.return_value = config

    mock_distance.side_effect = Exception("API down")
    mock_get_surge.return_value = 1.0

    # Should not raise; uses fallback 5km / 15min
    result = _call_estimate_fare((12.97, 77.59), (13.0, 77.6))
    assert result["distance_km"] == 5.0
    assert result["duration_min"] == 15.0


@patch("apps.rides.services.fare.get_surge")
@patch("apps.rides.services.fare.get_distance_and_duration")
@patch("apps.rides.services.fare.FareConfig")
def test_estimate_fare_surge_applied(mock_fare_config, mock_distance, mock_get_surge):
    config = MagicMock()
    config.base_fare = Decimal("50.00")
    config.per_km_rate = Decimal("12.00")
    config.per_min_rate = Decimal("1.00")
    config.base_distance_km = Decimal("2.0")
    config.minimum_fare = Decimal("40.00")
    mock_fare_config.get_for.return_value = config

    mock_distance.return_value = (5.0, 10.0)
    mock_get_surge.return_value = 2.0  # Double surge

    result_normal = _call_estimate_fare((12.97, 77.59), (13.0, 77.6))

    # Surge 2x should produce higher fare
    assert result_normal["surge_multiplier"] == 2.0


@patch("apps.rides.services.fare.get_surge")
@patch("apps.rides.services.fare.get_distance_and_duration")
@patch("apps.rides.services.fare.FareConfig")
def test_estimate_fare_enforces_minimum(mock_fare_config, mock_distance, mock_get_surge):
    config = MagicMock()
    config.base_fare = Decimal("0.00")
    config.per_km_rate = Decimal("0.00")
    config.per_min_rate = Decimal("0.00")
    config.base_distance_km = Decimal("100.0")  # base > actual → no extra charge
    config.minimum_fare = Decimal("99.00")
    mock_fare_config.get_for.return_value = config

    mock_distance.return_value = (1.0, 1.0)  # very short ride
    mock_get_surge.return_value = 1.0

    result = _call_estimate_fare((12.97, 77.59), (13.0, 77.6))
    assert result["estimated_fare"] >= Decimal("99.00")


def _call_estimate_fare(pickup, drop, vehicle_type="go"):
    from apps.rides.services.fare import estimate_fare
    return estimate_fare(pickup, drop, vehicle_type)
