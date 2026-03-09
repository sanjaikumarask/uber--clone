from unittest.mock import patch, MagicMock
from consumers.ride_events import send_to_dlq

@patch("consumers.ride_events.get_kafka_producer")
@patch("consumers.ride_events.logger")
def test_send_to_dlq_success(mock_logger, mock_get_producer):
    mock_producer = MagicMock()
    mock_get_producer.return_value = mock_producer
    send_to_dlq({"ride_id": 123}, "test failure")
    mock_producer.flush.assert_called_once()
    mock_logger.warning.assert_called_with("Event sent to DLQ: test failure")
