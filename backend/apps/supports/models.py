from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.rides.models import Ride


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN"
        RESOLVED = "RESOLVED"
        REJECTED = "REJECTED"

    class Reason(models.TextChoices):
        OVERCHARGED = "OVERCHARGED"
        DRIVER_MISCONDUCT = "DRIVER_MISCONDUCT"
        NO_SHOW_DISPUTE = "NO_SHOW_DISPUTE"
        ROUTE_DEVIATION = "ROUTE_DEVIATION"
        OTHER = "OTHER"

    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name="support_tickets",
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )

    category = models.CharField(max_length=64, blank=True, default="other")
    subject = models.CharField(max_length=255, blank=True, default="")
    reason = models.CharField(
        max_length=32,
        choices=Reason.choices,
        null=True,
        blank=True,
    )

    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_tickets",
    )

    resolution_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["ride", "status"]),
        ]

    def resolve(self, *, admin, note):
        if self.status != self.Status.OPEN:
            raise ValidationError("Ticket already resolved")

        self.status = self.Status.RESOLVED
        self.resolved_by = admin
        self.resolution_note = note
        self.resolved_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolution_note",
                "resolved_at",
            ]
        )

    def reject(self, *, admin, note):
        if self.status != self.Status.OPEN:
            raise ValidationError("Ticket already resolved")

        self.status = self.Status.REJECTED
        self.resolved_by = admin
        self.resolution_note = note
        self.resolved_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolution_note",
                "resolved_at",
            ]
        )


class Emergency(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active Emergency"
        RESOLVED = "RESOLVED", "Resolved"
        FALSE_ALARM = "FALSE_ALARM", "False Alarm"

    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name="emergencies",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergencies",
    )

    # Snapshot of location when SOS was pressed
    lat = models.FloatField()
    lng = models.FloatField()

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    resolution_note = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_emergencies",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Emergencies"

    def resolve(self, admin_user, note, status=Status.RESOLVED):
        self.status = status
        self.resolution_note = note
        self.resolved_at = timezone.now()
        self.resolved_by = admin_user
        self.save()


class FAQ(models.Model):
    class Audience(models.TextChoices):
        RIDER = "RIDER", "Rider"
        DRIVER = "DRIVER", "Driver"
        BOTH = "BOTH", "Both"

    class Category(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment & Billing"
        RIDE_ISSUE = "RIDE_ISSUE", "Ride Issues"
        ACCOUNT = "ACCOUNT", "Account & Settings"
        SAFETY = "SAFETY", "Safety"

    question = models.CharField(max_length=255)
    answer = models.TextField()
    audience = models.CharField(
        max_length=10, choices=Audience.choices, default=Audience.BOTH
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.RIDE_ISSUE
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"[{self.audience}] {self.question}"
