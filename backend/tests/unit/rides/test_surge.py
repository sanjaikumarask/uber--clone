from unittest.mock import patch
from apps.rides.services.surge_engine import recompute_surge

@patch("apps.rides.services.surge_engine.redis_client")
def test_surge_bounds(mock_redis):
    # CASE 1: High Demand
    # Demand 100, Supply 1 -> Surge 100.0 (Unclamped) -> Clamped 3.0 (SURGE_MAX)
    mock_redis.get.side_effect = ["100", "1"] 
    
    surge = recompute_surge("cell_123")
    assert surge == 3.0
    
    # CASE 2: Low Demand
    # Demand 1, Supply 100 -> Surge 0.01 (Unclamped) -> Clamped 1.0 (SURGE_MIN)
    mock_redis.get.side_effect = ["1", "100"] 
    surge = recompute_surge("cell_123")
    assert surge == 1.0

@patch("apps.rides.services.surge_engine.redis_client")
def test_surge_zero_supply(mock_redis):
    # CASE 3: Zero Supply
    mock_redis.get.side_effect = ["5", "0"] # Supply 0
    # Logic: if supply <= 0: surge = SURGE_MAX (3.0)
    
    surge = recompute_surge("cell_123")
    assert surge == 3.0
    
    # CASE 4: Negative Supply (Edge case)
    mock_redis.get.side_effect = ["5", "-1"] 
    surge = recompute_surge("cell_123")
    assert surge == 3.0

@patch("apps.rides.services.surge_engine.redis_client")
def test_surge_normal(mock_redis):
    # CASE 5: Normal Surge
    # Demand 20, Supply 10 -> Surge 2.0
    mock_redis.get.side_effect = ["20", "10"]
    
    surge = recompute_surge("cell_123")
    assert surge == 2.0
    
    mock_redis.setex.assert_called_with(
        "geo:cell_123:surge",
        60,
        2.0
    )
