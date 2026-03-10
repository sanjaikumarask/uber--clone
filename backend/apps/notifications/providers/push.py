import logging

from django.utils import timezone
from exponent_server_sdk import PushClient, PushMessage

logger = logging.getLogger(__name__)


def send_push(notification):
    """
    Sends an Expo push notification.
    Expects user.expo_push_token to be set.
    """
    user = notification.user
    token = getattr(user, "expo_push_token", None)

    if not token:
        # Silently fail if no token, or raise ValueError if mandatory
        return {"status": "skipped", "reason": "No push token"}

    payload = notification.payload
    title = payload.get("title", "Uber Clone")
    body = payload.get("body", "")
    data = payload.get("data", {})

    try:
        PushClient().publish(
            PushMessage(to=token, title=title, body=body, data=data, sound="default")
        )
        return {
            "channel": "push",
            "sent_at": timezone.now().isoformat(),
            "to": token,
            "status": "success",
        }
    except Exception as exc:
        logger.error(f"Push failed: {exc}")
        raise
