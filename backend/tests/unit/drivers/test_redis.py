from unittest.mock import patch, MagicMock
from apps.drivers.redis import update_driver_location, get_driver_last_point, remove_driver_from_geo

@patch("apps.common.fraud.validate_gps_velocity")
@patch("apps.drivers.redis.redis_client")
@patch("apps.drivers.redis.time.time")
def test_update_location(mock_time, mock_redis, mock_validate):
    mock_time.return_value = 1000
    mock_validate.return_value = True
    
    update_driver_location(1, 10.0, 20.0)
    
    # Verify Geo Add (uses execute_command in current implementation)
    mock_redis.execute_command.assert_any_call(
        "GEOADD",
        "drivers:geo",
        20.0,
        10.0,
        "1"
    )
    
    # Verify Heartbeat
    mock_redis.setex.assert_called_with(
        "driver:1:last_seen",
        60,
        1000
    )

@patch("apps.drivers.redis.redis_client")
def test_get_last_point(mock_redis):
    mock_redis.hgetall.return_value = {"lat": "10.0", "lng": "20.0"}
    res = get_driver_last_point(1)
    assert res == (10.0, 20.0)

@patch("apps.drivers.redis.redis_client")
def test_remove_driver(mock_redis):
    remove_driver_from_geo(1)
    
    # Verify Geo Remove
    mock_redis.execute_command.assert_any_call(
        "ZREM",
        "drivers:geo",
        "1"
    )
    
    # Verify deletions
    # driver:1:meta (deprecated but still in code), driver:1:last_seen, driver:1:last_point
    assert mock_redis.delete.call_count >= 2
