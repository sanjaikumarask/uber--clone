from unittest.mock import patch, MagicMock
from apps.rides.services.realtime import broadcast_ride_update

@patch("apps.rides.services.realtime.get_channel_layer")
@patch("apps.rides.services.realtime.async_to_sync")
def test_broadcast(mock_async, mock_get_layer):
    mock_layer = MagicMock()
    mock_get_layer.return_value = mock_layer
    
    # Mock async_to_sync return value (which is callable)
    mock_wrapper = MagicMock()
    mock_async.return_value = mock_wrapper
    
    broadcast_ride_update(123, event="TEST_EVENT", data={"foo": "bar"})
    
    mock_get_layer.assert_called_once()
    
    # async_to_sync(layer.group_send) is called.
    # So async_to_sync called with layer.group_send
    mock_async.assert_called_once_with(mock_layer.group_send)
    
    # Then wrapper called with args
    mock_wrapper.assert_called_once_with(
        "ride_123",
        {
            "type": "ride_update",
            "event": "TEST_EVENT",
            "data": {"foo": "bar"}
        }
    )
