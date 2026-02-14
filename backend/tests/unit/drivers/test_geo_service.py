from unittest.mock import patch, MagicMock
from apps.drivers.services.geo import add_driver_to_geo, remove_driver_from_geo, get_nearby_driver_ids

@patch("apps.drivers.services.geo.redis_client")
def test_add_driver(mock_redis):
    add_driver_to_geo(driver_id=1, lat=10, lng=20)
    mock_redis.geoadd.assert_called_with("drivers:geo", (20, 10, "1"))

@patch("apps.drivers.services.geo.redis_client")
def test_remove_driver(mock_redis):
    remove_driver_from_geo(driver_id=1)
    mock_redis.zrem.assert_called_with("drivers:geo", "1")

@patch("apps.drivers.services.geo.redis_client")
def test_get_nearby(mock_redis):
    mock_redis.geosearch.return_value = ["1", "2", "3"]
    
    ids = get_nearby_driver_ids(lat=10, lng=20, radius_km=5)
    
    assert ids == [1, 2, 3]
    mock_redis.geosearch.assert_called_with(
        "drivers:geo", 
        longitude=20, 
        latitude=10, 
        radius=5, 
        unit="km", 
        count=5
    )
