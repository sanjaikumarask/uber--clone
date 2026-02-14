from twilio.rest import Client
from django.conf import settings
from django.utils import timezone

def send_sms(notification):
    """
    Raises exception on failure.
    """

    payload = notification.payload
    message_body = payload.get("body")

    if not message_body:
        raise ValueError("SMS body missing")

    phone = getattr(notification.user, "phone_number", None)
    if not phone:
        raise ValueError("User has no phone number")

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
    )

    msg = client.messages.create(
        body=message_body,
        from_=settings.TWILIO_FROM_NUMBER,
        to=phone,
    )

    return {
        "channel": "sms",
        "sid": msg.sid,
        "sent_at": timezone.now().isoformat(),
        "to": phone,
    }
