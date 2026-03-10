# backend/apps/notifications/services/router.py

from ..providers.websocket import send_ws

try:
    from ..providers.email import send_email
except ImportError:
    send_email = None

try:
    from ..providers.sms import send_sms
except ImportError:
    send_sms = None

try:
    from ..providers.push import send_push
except ImportError:
    send_push = None


def route_notification(notification):
    """
    Routes the notification to the correct provider based on channel.
    """
    channel = notification.channel.lower()

    if channel in {"ws", "websocket"}:
        send_ws(notification)

    elif channel == "email" and send_email:
        send_email(notification)

    elif channel == "sms" and send_sms:
        send_sms(notification)

    elif channel == "push" and send_push:
        send_push(notification)
