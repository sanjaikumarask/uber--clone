from unittest.mock import MagicMock, patch
from apps.notifications.services.router import route_notification

@patch("apps.notifications.services.router.send_ws")
def test_route_ws(mock_ws):
    notification = MagicMock()
    notification.channel = "ws"
    
    route_notification(notification)
    
    mock_ws.assert_called_once_with(notification)

@patch("apps.notifications.services.router.send_email")
def test_route_email(mock_email):
    notification = MagicMock()
    notification.channel = "email"
    
    route_notification(notification)
    
    mock_email.assert_called_once_with(notification)

@patch("apps.notifications.services.router.send_sms")
def test_route_sms(mock_sms):
    notification = MagicMock()
    notification.channel = "sms"
    
    route_notification(notification)
    
    mock_sms.assert_called_once_with(notification)
