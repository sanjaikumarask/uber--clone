from django.db import models
from django.utils import timezone


class DriverIncentive(models.Model):
    class Type(models.TextChoices):
        STREAK = "STREAK", "Ride Streak (N rides)"
        PEAK = "PEAK", "Peak Hour Bonus"
        ZONE = "ZONE", "Geo-Zone Bonus"

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.PEAK)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Condition stored as JSON (e.g. {"rides_required": 5, "start_hour": 17, "end_hour": 20})
    condition = models.JSONField(default=dict, help_text="Config for incentive rules")

    reward_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_per_day = models.PositiveIntegerField(default=1)

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    city = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.type})"

    def is_valid_now(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to


class DriverIncentiveProgress(models.Model):
    """Tracks progress for multi-ride incentives like STREAK"""

    class Meta:
        unique_together = ("driver", "incentive")

    driver = models.ForeignKey("drivers.Driver", on_delete=models.CASCADE)
    incentive = models.ForeignKey(DriverIncentive, on_delete=models.CASCADE)

    current_count = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)


class DriverIncentiveEarning(models.Model):
    incentive = models.ForeignKey(DriverIncentive, on_delete=models.CASCADE)
    driver = models.ForeignKey("drivers.Driver", on_delete=models.CASCADE)
    ride = models.ForeignKey("rides.Ride", on_delete=models.CASCADE)

    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
