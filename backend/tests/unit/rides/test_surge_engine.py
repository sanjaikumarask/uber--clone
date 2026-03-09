import pytest
from unittest.mock import patch, MagicMock
from apps.rides.services.surge_engine import (
    cell_id_from_lat_lng,
    recompute_surge,
    increment_demand,
    decrement_demand,
    increment_supply,
    decrement_supply
)

@pytest.mark.django_db
class TestSurgeEngine:

    def test_cell_id_generation(self):
        assert cell_id_from_lat_lng(12.9716, 77.5946) == "12.97:77.59"
        assert cell_id_from_lat_lng(12.978, 77.592) == "12.98:77.59"

    @patch("apps.rides.services.surge_engine.redis_client")
    def test_recompute_surge_no_supply(self, mock_redis):
        mock_redis.get.side_effect = ["10", "0"] # demand=10, supply=0
        surge = recompute_surge("test_cell")
        assert surge == 3.0 # SURGE_MAX
        mock_redis.setex.assert_called()

    @patch("apps.rides.services.surge_engine.redis_client")
    def test_recompute_surge_normal(self, mock_redis):
        mock_redis.get.side_effect = ["10", "5"] # demand=10, supply=5
        surge = recompute_surge("test_cell")
        assert surge == 2.0
        mock_redis.setex.assert_called_with("geo:test_cell:surge", 60, 2.0)

    @patch("apps.rides.services.surge_engine.redis_client")
    def test_recompute_surge_clamped_min(self, mock_redis):
        mock_redis.get.side_effect = ["1", "5"] # demand=1, supply=5 -> 0.2
        surge = recompute_surge("test_cell")
        assert surge == 1.0 # SURGE_MIN
        
    @patch("apps.rides.services.surge_engine.redis_client")
    def test_recompute_surge_clamped_max(self, mock_redis):
        mock_redis.get.side_effect = ["100", "2"] # demand=100, supply=2 -> 50.0
        surge = recompute_surge("test_cell")
        assert surge == 3.0 # SURGE_MAX

    @patch("apps.rides.services.surge_engine.recompute_surge")
    @patch("apps.rides.services.surge_engine.redis_client")
    def test_counters(self, mock_redis, mock_recompute):
        increment_demand("cell1")
        mock_redis.incr.assert_called_with("geo:cell1:demand")
        mock_recompute.assert_called_with("cell1")
        
        decrement_demand("cell1")
        mock_redis.decr.assert_called_with("geo:cell1:demand")
        
        increment_supply("cell1")
        mock_redis.incr.assert_called_with("geo:cell1:supply")
        
        decrement_supply("cell1")
        mock_redis.decr.assert_called_with("geo:cell1:supply")
