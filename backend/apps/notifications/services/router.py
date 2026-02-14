# backend/apps/notifications/services/router.py

from ..providers.websocket import send_ws
# Import other providers only if they exist to avoid ImportErrors
try:
    from ..providers.email import send_email
except ImportError:
    send_email = None

try:
    from ..providers.sms import send_sms
except ImportError:
    send_sms = None

def route_notification(notification):
    """
    Routes the notification to the correct provider based on channel.
    """
    if notification.channel == "ws" or notification.channel == "WEBSOCKET":
        send_ws(notification)

    elif notification.channel == "email" or notification.channel == "EMAIL":
        if send_email:
            # Add preference check here if needed
            send_email(notification)

    elif notification.channel == "sms" or notification.channel == "SMS":
        if send_sms:
            # Add preference check here if needed
            send_sms(notification)
            
    elif notification.channel == "push" or notification.channel == "PUSH":
        # Placeholder for Push Notifications (FCM/APNS)
        pass