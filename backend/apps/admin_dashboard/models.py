# apps/admin_dashboard/models.py
from django.db import models


class SystemLog(models.Model):
    class LogType(models.TextChoices):
        ERROR = "ERROR", "Error"
        WARNING = "WARNING", "Warning"
        INFO = "INFO", "Info"
        PAYMENT_FAILURE = "PAYMENT_FAILURE", "Payment Failure"
        RIDE_STUCK = "RIDE_STUCK", "Ride Stuck"
        WS_DISCONNECT = "WS_DISCONNECT", "WebSocket Disconnect"

    type = models.CharField(
        max_length=20,
        choices=LogType.choices,
        default=LogType.INFO,
        db_index=True,
    )
    message = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "System Alert"
        verbose_name_plural = "System Alerts"

    def __str__(self):
        return f"[{self.type}] {self.message[:50]} at {self.created_at}"
