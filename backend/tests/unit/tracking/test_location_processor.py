from unittest.mock import MagicMock, patch

import pytest

from apps.tracking.services import LocationProcessor


# ─── filter_noisy_ping ────────────────────────────────────────────────────────

def test_filter_noisy_ping_high_accuracy():
    assert LocationProcessor.filter_noisy_ping(150) is True


def test_filter_noisy_ping_low_accuracy():
    assert LocationProcessor.filter_noisy_ping(50) is False


def test_filter_noisy_ping_exact_boundary():
    # > 120 is noisy, = 120 is not
    assert LocationProcessor.filter_noisy_ping(120) is False
    assert LocationProcessor.filter_noisy_ping(121) is True


def test_filter_noisy_ping_none():
    assert LocationProcessor.filter_noisy_ping(None) is False


def test_filter_noisy_ping_zero():
    assert LocationProcessor.filter_noisy_ping(0) is False


# ─── detect_fraud ─────────────────────────────────────────────────────────────

def test_detect_fraud_fast_speed_over_500():
    """Speed > 500 km/h is teleportation and returns True."""
    ride = MagicMock()
    ride.id = 1
    result = LocationProcessor.detect_fraud(ride, delta_km=100, elapsed_seconds=0.5)
    assert result is True


def test_detect_fraud_fast_but_not_teleportation():
    """Speed > 150 km/h but < 500 flags ride but returns False."""
    ride = MagicMock()
    ride.id = 1
    # 200 km/h
    result = LocationProcessor.detect_fraud(ride, delta_km=11.1, elapsed_seconds=200)
    # 11.1km / 200s * 3600 = 199.8 km/h (> 150, < 500 → flagged but not teleport)
    assert result is False
    assert ride.is_fraud_flagged is True
    ride.save.assert_called_once_with(update_fields=["is_fraud_flagged"])


def test_detect_fraud_normal_speed():
    """Normal speed does not flag ride."""
    ride = MagicMock()
    ride.id = 1
    # 30 km/h 
    result = LocationProcessor.detect_fraud(ride, delta_km=0.25, elapsed_seconds=30)
    assert result is False
    ride.save.assert_not_called()


def test_detect_fraud_zero_elapsed():
    """Zero elapsed time returns False safely."""
    ride = MagicMock()
    result = LocationProcessor.detect_fraud(ride, delta_km=10, elapsed_seconds=0)
    assert result is False


def test_detect_fraud_zero_delta():
    """Zero distance returns False."""
    ride = MagicMock()
    result = LocationProcessor.detect_fraud(ride, delta_km=0, elapsed_seconds=60)
    assert result is False


# ─── calculate_eta ────────────────────────────────────────────────────────────

def test_calculate_eta_no_ride():
    result = LocationProcessor.calculate_eta(None, 12.97, 77.59)
    assert result is None


@patch("apps.tracking.geo.haversine_m")
def test_calculate_eta_assigned_uses_pickup(mock_haversine):
    mock_haversine.return_value = 5000  # 5km

    ride = MagicMock()
    ride.status = "ASSIGNED"
    ride.Status = MagicMock()
    ride.Status.ASSIGNED = "ASSIGNED"
    ride.Status.ARRIVED = "ARRIVED"
    ride.pickup_lat = 12.97
    ride.pickup_lng = 77.59

    eta = LocationProcessor.calculate_eta(ride, 12.98, 77.60)

    # 5km / 0.41 km/min ≈ 12 min
    assert eta > 0


@patch("apps.tracking.geo.haversine_m")
def test_calculate_eta_ongoing_uses_drop(mock_haversine):
    mock_haversine.return_value = 10000  # 10km

    ride = MagicMock()
    ride.status = "ONGOING"
    ride.Status = MagicMock()
    ride.Status.ASSIGNED = "ASSIGNED"
    ride.Status.ARRIVED = "ARRIVED"
    ride.drop_lat = 13.00
    ride.drop_lng = 77.70

    eta = LocationProcessor.calculate_eta(ride, 12.97, 77.59)

    assert eta > 0


@patch("apps.tracking.geo.haversine_m")
def test_calculate_eta_minimum_is_1(mock_haversine):
    """ETA should never be 0 even if distance is near 0."""
    mock_haversine.return_value = 1  # 1 meter

    ride = MagicMock()
    ride.status = "ONGOING"
    ride.Status = MagicMock()
    ride.Status.ASSIGNED = "ASSIGNED"
    ride.Status.ARRIVED = "ARRIVED"
    ride.drop_lat = 12.97
    ride.drop_lng = 77.59

    eta = LocationProcessor.calculate_eta(ride, 12.97, 77.59)
    assert eta >= 1
