from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
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
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )

    reason = models.CharField(
        max_length=32,
        choices=Reason.choices,
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

    resolution_note = models.TextField(null=True, blank=True)

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

        self.save(update_fields=[
            "status",
            "resolved_by",
            "resolution_note",
            "resolved_at",
        ])

    def reject(self, *, admin, note):
        if self.status != self.Status.OPEN:
            raise ValidationError("Ticket already resolved")

        self.status = self.Status.REJECTED
        self.resolved_by = admin
        self.resolution_note = note
        self.resolved_at = timezone.now()

        self.save(update_fields=[
            "status",
            "resolved_by",
            "resolution_note",
            "resolved_at",
        ])
