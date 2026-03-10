import pytest
from unittest.mock import patch, MagicMock
from apps.common.ordering import SequenceFencer, RIDE_STATUS_RANK

class TestOrdering:
    def test_ride_status_rank(self):
        assert RIDE_STATUS_RANK["SEARCHING"] == 1
        assert RIDE_STATUS_RANK["COMPLETED"] == 10
        
    @patch('apps.common.ordering.redis_client.register_script')
    def test_fence_event_success(self, mock_script):
        mock_callable = MagicMock(return_value=1)
        mock_script.return_value = mock_callable
        
        result = SequenceFencer.fence_event("ride", "1", 2)
        assert result is True
        mock_script.assert_called_once()
        mock_callable.assert_called_once()
        args, kwargs = mock_callable.call_args
        assert kwargs["keys"] == ["fence:ride:1"]
        assert kwargs["args"] == [2, 86400]

    @patch('apps.common.ordering.redis_client.register_script')
    def test_fence_event_duplicate(self, mock_script):
        mock_callable = MagicMock(return_value=0)
        mock_script.return_value = mock_callable
        
        result = SequenceFencer.fence_event("ride", "1", 1)
        assert result is False

    @patch('apps.common.ordering.redis_client.get')
    def test_get_rank(self, mock_get):
        mock_get.return_value = b'5'
        rank = SequenceFencer.get_rank("ride", "1")
        assert rank == 5
        
        mock_get.return_value = None
        rank = SequenceFencer.get_rank("ride", "2")
        assert rank == 0

    @patch('apps.common.ordering.redis_client.delete')
    def test_clear_fence(self, mock_delete):
        SequenceFencer.clear_fence("ride", "1")
        mock_delete.assert_called_once_with("fence:ride:1")
