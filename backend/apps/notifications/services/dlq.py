from ..models import NotificationDeadLetter

def send_to_dlq(notification, reason: str):
    NotificationDeadLetter.objects.create(
        notification=notification,
        reason=reason,
    )
