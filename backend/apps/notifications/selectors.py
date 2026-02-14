from .models import Notification, NotificationPreference
from .enums import NotificationStatus

def get_pending_notifications(user):
    return Notification.objects.filter(
        user=user, status=NotificationStatus.PENDING
    )

def get_user_preferences(user):
    return NotificationPreference.objects.get_or_create(user=user)[0]
