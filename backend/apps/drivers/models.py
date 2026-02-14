from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

class Driver(models.Model):
    class Status(models.TextChoices):
        OFFLINE = "OFFLINE", "Offline"
        ONLINE = "ONLINE", "Online"
        BUSY = "BUSY", "Busy"
        BLOCKED = "BLOCKED", "Blocked"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver",
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OFFLINE,
        db_index=True,
    )

    # Bank Details (for Payouts)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11, blank=True, null=True)

    last_lat = models.FloatField(null=True, blank=True)
    last_lng = models.FloatField(null=True, blank=True)
    total_rides = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ALLOWED_TRANSITIONS = {
        Status.OFFLINE: {Status.ONLINE},
        Status.ONLINE: {Status.BUSY, Status.OFFLINE},
        Status.BUSY: {Status.ONLINE},
    }

    def transition_to(self, new_status):
        if new_status == self.status:
            return
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Invalid driver transition {self.status} -> {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"Driver #{self.id} ({self.status})"


class DriverStats(models.Model):
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        related_name="stats",
    )

    total_rides = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    cancelled_rides = models.PositiveIntegerField(default=0)
    no_shows = models.PositiveIntegerField(default=0)
    
    # ------------------------------------------
    # Rejection Limits Logic
    # ------------------------------------------
    rejection_count_today = models.PositiveIntegerField(default=0)
    last_rejection_date = models.DateField(null=True, blank=True)

    rating_sum = models.PositiveIntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    avg_rating = models.FloatField(default=5.0)

    is_suspended = models.BooleanField(default=False)
    suspended_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def check_and_reset_daily_stats(self):
        """Resets rejection count if the day has changed."""
        today = timezone.now().date()
        if self.last_rejection_date != today:
            self.rejection_count_today = 0
            self.last_rejection_date = today
            self.save(update_fields=["rejection_count_today", "last_rejection_date"])

    def update_rating(self, rating: int):
        self.rating_sum += rating
        self.rating_count += 1
        self.avg_rating = round(self.rating_sum / self.rating_count, 2)
        self.save(update_fields=["rating_sum", "rating_count", "avg_rating", "updated_at"])