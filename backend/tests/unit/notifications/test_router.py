from unittest.mock import MagicMock, patch

from apps.notifications.services.router import route_notification

def test_route_notification_websocket():
    notification = MagicMock()
    notification.channel = "websocket"
    
    with patch("apps.notifications.services.router.send_ws") as mock_send:
        route_notification(notification)
        mock_send.assert_called_once_with(notification)

def test_route_notification_email():
    notification = MagicMock()
    notification.channel = "email"
    
    with patch("apps.notifications.services.router.send_email") as mock_send:
        # We need to make sure send_email is truthy for the if check
        # Actually in router.py it's imported at top-level. 
        # If the mock is active, it will be truthy.
        route_notification(notification)
        mock_send.assert_called_once_with(notification)

def test_route_notification_sms():
    notification = MagicMock()
    notification.channel = "sms"
    
    with patch("apps.notifications.services.router.send_sms") as mock_send:
        route_notification(notification)
        mock_send.assert_called_once_with(notification)

def test_route_notification_push():
    notification = MagicMock()
    notification.channel = "push"
    
    with patch("apps.notifications.services.router.send_push") as mock_send:
        route_notification(notification)
        mock_send.assert_called_once_with(notification)

def test_route_notification_unknown_channel():
    notification = MagicMock()
    notification.channel = "unknown"
    
    # Verify no exception
    route_notification(notification)
