from apps.notifications.models import Notification
from apps.notifications.tasks import deliver_notification


def create_and_enqueue_notification(
    *,
    user_id: int,
    event_type: str,
    channel: str,
    payload: dict,
):
    """
    Single entry point to create & enqueue notifications.
    """
    notification = Notification.objects.create(
        user_id=user_id,
        type=event_type,
        channel=channel,
        payload=payload,
    )

    # ALWAYS async
    deliver_notification.delay(notification.id)
