from unittest.mock import MagicMock, patch, AsyncMock
import math

import pytest

from apps.rides.services.deviation import (
    haversine_distance,
    point_to_segment_distance,
    check_route_deviation,
)


# ─── haversine_distance ───────────────────────────────────────────────────────

def test_haversine_same_points():
    assert haversine_distance(12.97, 77.59, 12.97, 77.59) == pytest.approx(0.0, abs=1)


def test_haversine_known_distance():
    # Chennai to Bangalore ~300km
    dist = haversine_distance(13.0827, 80.2707, 12.9716, 77.5946)
    assert 280_000 < dist < 340_000  # meters


def test_haversine_symmetry():
    d1 = haversine_distance(12.97, 77.59, 13.08, 80.27)
    d2 = haversine_distance(13.08, 80.27, 12.97, 77.59)
    assert d1 == pytest.approx(d2, rel=1e-6)


# ─── point_to_segment_distance ───────────────────────────────────────────────

def test_point_to_segment_on_segment():
    # Point is near the midpoint of a horizontal segment
    s1 = (0.0, 0.0)
    s2 = (0.0, 1.0)
    pt = (0.0, 0.5)
    dist = point_to_segment_distance(pt, s1, s2)
    # Point is on the segment, distance should be ~0
    assert dist < 1000  # very small in haversine meters


def test_point_to_segment_zero_length():
    # Degenerate segment (same start and end)
    s1 = (12.97, 77.59)
    s2 = (12.97, 77.59)
    pt = (12.98, 77.60)
    dist = point_to_segment_distance(pt, s1, s2)
    # Should fall back to haversine of pt to s1
    expected = haversine_distance(12.98, 77.60, 12.97, 77.59)
    assert dist == pytest.approx(expected, rel=1e-6)


def test_point_to_segment_before_start():
    # t < 0 → clamp to s1
    s1 = (1.0, 1.0)
    s2 = (2.0, 2.0)
    pt = (0.0, 0.0)
    dist = point_to_segment_distance(pt, s1, s2)
    expected = haversine_distance(0, 0, 1, 1)
    assert dist == pytest.approx(expected, rel=1e-4)


def test_point_to_segment_after_end():
    # t > 1 → clamp to s2
    s1 = (1.0, 1.0)
    s2 = (2.0, 2.0)
    pt = (3.0, 3.0)
    dist = point_to_segment_distance(pt, s1, s2)
    expected = haversine_distance(3, 3, 2, 2)
    assert dist == pytest.approx(expected, rel=1e-4)


# ─── check_route_deviation ────────────────────────────────────────────────────

def test_no_polyline_returns_false():
    ride = MagicMock()
    ride.planned_route_polyline = None
    driver = MagicMock()

    result, dist = check_route_deviation(driver, ride, 12.97, 77.59)
    assert result is False
    assert dist == 0


@patch("apps.rides.services.deviation.polyline")
def test_empty_polyline_returns_false(mock_polyline):
    ride = MagicMock()
    ride.planned_route_polyline = "dummy"
    mock_polyline.decode.return_value = []

    driver = MagicMock()
    result, dist = check_route_deviation(driver, ride, 12.97, 77.59)
    assert result is False


@patch("apps.rides.services.deviation.polyline")
def test_single_segment_polyline_not_deviated(mock_polyline):
    # Two points, driver is on the segment
    ride = MagicMock()
    ride.planned_route_polyline = "dummy"
    ride.id = 10
    mock_polyline.decode.return_value = [(12.97, 77.59), (12.98, 77.60)]

    driver = MagicMock()
    # Driver is right at the first polyline point (no deviation)
    result, dist = check_route_deviation(driver, ride, 12.97, 77.59, threshold_m=500)
    assert result is False


@patch("apps.rides.services.deviation.get_channel_layer")
@patch("apps.rides.services.deviation.async_to_sync")
@patch("apps.rides.services.deviation.polyline")
def test_large_deviation_triggers_alert(mock_polyline, mock_async_sync, mock_get_layer):
    ride = MagicMock()
    ride.id = 99
    ride.planned_route_polyline = "dummy"
    # Very far route: Chennai
    mock_polyline.decode.return_value = [(12.97, 77.59), (12.98, 77.60)]

    mock_channel_layer = MagicMock()
    mock_get_layer.return_value = mock_channel_layer
    mock_async_sync.return_value = MagicMock()

    driver = MagicMock()
    driver.id = 1

    # Patch cache.get to return None (no recent alert throttle)
    with patch("django.core.cache.cache") as mock_cache:
        mock_cache.get.return_value = None
        result, dist = check_route_deviation(driver, ride, 19.07, 72.87, threshold_m=500)

    assert result is True
    assert dist > 500


@patch("apps.rides.services.deviation.polyline")
def test_exception_returns_false(mock_polyline):
    ride = MagicMock()
    ride.planned_route_polyline = "bad"
    mock_polyline.decode.side_effect = Exception("bad data")

    driver = MagicMock()
    result, dist = check_route_deviation(driver, ride, 12.97, 77.59)
    assert result is False
    assert dist == 0
