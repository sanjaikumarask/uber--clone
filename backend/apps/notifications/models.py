from django.db import models
from django.conf import settings
from .enums import NotificationStatus

User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.CharField(max_length=20)
    type = models.CharField(max_length=50)
    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=[
            (NotificationStatus.PENDING, "Pending"),
            (NotificationStatus.SENT, "Sent"),
            (NotificationStatus.FAILED, "Failed"),
        ],
        default=NotificationStatus.PENDING,
    )

    retry_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "retry_count"]),
        ]

    def __str__(self):
        return f"Notification<{self.id}> {self.type} [{self.status}]"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"NotificationPreference<{self.user_id}>"


class NotificationDeadLetter(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DLQ: {self.notification_id}"
