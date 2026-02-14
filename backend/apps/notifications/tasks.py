from celery import shared_task
from django.utils import timezone

from .models import Notification
from .services.dispatcher import dispatch
from .services.retry import should_retry, get_retry_delay
from .services.dlq import send_to_dlq
from .enums import NotificationStatus


@shared_task(bind=True, max_retries=0)
def deliver_notification(self, notification_id: int):
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return

    try:
        dispatch(notification)

        notification.status = NotificationStatus.SENT
        notification.sent_at = timezone.now()
        notification.save(update_fields=["status", "sent_at"])

    except Exception as exc:
        notification.retry_count += 1

        if should_retry(notification):
            notification.save(update_fields=["retry_count"])

            delay = get_retry_delay(notification)
            self.apply_async(
                args=[notification.id],
                countdown=delay,
            )
        else:
            notification.status = NotificationStatus.FAILED
            notification.save(update_fields=["retry_count", "status"])
            send_to_dlq(notification, reason=str(exc))
