from unittest.mock import patch, MagicMock
from apps.common.ordering import SequenceFencer

@patch("apps.common.ordering.redis_client")
def test_sequence_fencer_logic(mock_redis):
    # Mock register_script result
    mock_script = MagicMock()
    mock_redis.register_script.return_value = mock_script
    
    # Test True path
    mock_script.return_value = 1
    assert SequenceFencer.fence_event("ride", 1, 5) is True
    
    # Test False path
    mock_script.return_value = 0
    assert SequenceFencer.fence_event("ride", 1, 4) is False

@patch("apps.common.ordering.redis_client")
def test_sequence_fencer_utils(mock_redis):
    mock_redis.get.return_value = b"5"
    assert SequenceFencer.get_rank("ride", 1) == 5
    
    SequenceFencer.clear_fence("ride", 1)
    mock_redis.delete.assert_called()
