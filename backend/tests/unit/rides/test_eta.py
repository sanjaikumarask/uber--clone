import pytest
from unittest.mock import patch, MagicMock
from apps.rides.services.eta import calculate_eta_minutes, haversine_km, calculate_eta
from apps.rides.services.eta_cache import cache_planned_eta, get_cached_eta
from apps.rides.services.eta_updater import update_eta_if_needed

def test_haversine_km_logic():
    # Known distance: (0,0) to (1,0) deg ~ 111km
    dist = haversine_km(0, 0, 1, 0)
    assert 110 < dist < 112

def test_calculate_eta_minutes():
    # 25 km at 25kmph = 1 hour = 60 min
    assert calculate_eta_minutes(25.0) == 60
    # 50 km = 120 min
    assert calculate_eta_minutes(50.0) == 120
    # 0.1km -> 1 min min
    assert calculate_eta_minutes(0.1) == 1

def test_calculate_eta_helper():
    with patch("apps.rides.services.eta.haversine_km", return_value=25.0):
        # 25km -> 60min
        assert calculate_eta(0,0,1,1) == 60

@patch("apps.rides.services.eta_cache.redis_client")
def test_cache_eta(mock_redis):
    cache_planned_eta(123, 15.5)
    mock_redis.setex.assert_called_with("ride:123:eta", 30, 15)

@patch("apps.rides.services.eta_cache.redis_client")
def test_get_eta(mock_redis):
    mock_redis.get.return_value = "20"
    eta = get_cached_eta(123)
    assert eta == 20
    mock_redis.get.assert_called_with("ride:123:eta")

@patch("apps.rides.services.eta_updater.calculate_eta")
@patch("apps.rides.services.eta_updater.get_cached_eta")
@patch("apps.rides.services.eta_updater.set_cached_eta")
def test_update_eta_if_needed_cached(mock_set, mock_get, mock_calc):
    # CASE 1: Cache exists
    mock_get.return_value = 15
    ride = MagicMock()
    ride.id = 1
    
    res = update_eta_if_needed(ride=ride, driver_lat=10, driver_lng=10)
    assert res == 15
    mock_calc.assert_not_called()

@patch("apps.rides.services.eta_updater.calculate_eta")
@patch("apps.rides.services.eta_updater.get_cached_eta")
@patch("apps.rides.services.eta_updater.set_cached_eta")
def test_update_eta_if_needed_miss(mock_set, mock_get, mock_calc):
    # CASE 2: Cache miss
    mock_get.return_value = None
    mock_calc.return_value = 25
    ride = MagicMock()
    ride.id = 1
    ride.drop_lat = 20
    ride.drop_lng = 20
    
    res = update_eta_if_needed(ride=ride, driver_lat=10, driver_lng=10)
    assert res == 25
    mock_set.assert_called_once_with(1, 25)
    # verify call to calculate
    mock_calc.assert_called_once()
