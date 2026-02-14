from unittest.mock import patch, MagicMock
from apps.drivers.redis import update_driver_location, get_driver_last_point, remove_driver_from_geo

@patch("apps.drivers.redis.redis_client")
@patch("apps.drivers.redis.time.time")
def test_update_location(mock_time, mock_redis):
    mock_time.return_value = 1000
    
    update_driver_location(1, 10.0, 20.0)
    
    # Verify Geo Add
    mock_redis.geoadd.assert_called_with("drivers:live", 20.0, 10.0, "driver:1")
    
    # Verify Meta
    # call_args for hset
    args, kwargs = mock_redis.hset.call_args
    # hset(name, mapping=...)
    assert args[0] == "driver:1:meta"
    assert kwargs['mapping']['last_seen'] == 1000

@patch("apps.drivers.redis.redis_client")
def test_get_last_point(mock_redis):
    mock_redis.hgetall.return_value = {"lat": "10.0", "lng": "20.0"}
    res = get_driver_last_point(1)
    assert res == (10.0, 20.0)

@patch("apps.drivers.redis.redis_client")
def test_remove_driver(mock_redis):
    remove_driver_from_geo(1)
    mock_redis.zrem.assert_called_with("drivers:live", "driver:1")
    # Verify deletions
    assert mock_redis.delete.call_count >= 2
