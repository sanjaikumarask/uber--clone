# apps/rides/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from apps.drivers.models import Driver


class Ride(models.Model):
    class Status(models.TextChoices):
        SEARCHING = "SEARCHING"
        OFFERED = "OFFERED"
        ASSIGNED = "ASSIGNED"
        ARRIVED = "ARRIVED"
        ONGOING = "ONGOING"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        NO_SHOW = "NO_SHOW"

    class CancelledBy(models.TextChoices):
        RIDER = "RIDER"
        DRIVER = "DRIVER"
        SYSTEM = "SYSTEM"

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rides",
    )

    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rides",
    )

    # --------------------
    # Location
    # --------------------
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    drop_lat = models.FloatField()
    drop_lng = models.FloatField()

    # --------------------
    # Planned route
    # --------------------
    planned_route_polyline = models.TextField(null=True, blank=True)
    planned_distance_km = models.FloatField(null=True, blank=True)
    planned_duration_min = models.FloatField(null=True, blank=True)

    # --------------------
    # Matching (CRITICAL)
    # --------------------
    candidate_driver_ids = models.JSONField(
        default=list,
        help_text="Ordered list of nearby driver IDs for matching",
    )
    rejected_driver_ids = models.JSONField(
        default=list,
        help_text="List of drivers who rejected or timed out",
    )

    search_attempt = models.PositiveIntegerField(default=0)

    # --------------------
    # Actual tracking
    # --------------------
    actual_distance_km = models.FloatField(default=0.0)
    last_snapped_lat = models.FloatField(null=True, blank=True)
    last_snapped_lng = models.FloatField(null=True, blank=True)

    # --------------------
    # Ride state
    # --------------------
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SEARCHING,
        db_index=True,
    )

    # --------------------
    # Fare
    # --------------------
    base_fare = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    final_fare = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # --------------------
    # OTP / arrival
    # --------------------
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)

    # --------------------
    # Cancellation
    # --------------------
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(
        max_length=16,
        choices=CancelledBy.choices,
        null=True,
        blank=True,
    )
    no_show_marked_at = models.DateTimeField(null=True, blank=True)

    # --------------------
    # Audit
    # --------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ALLOWED_TRANSITIONS = {
        Status.SEARCHING: {Status.OFFERED, Status.CANCELLED},
        Status.OFFERED: {Status.ASSIGNED, Status.SEARCHING, Status.CANCELLED},
        Status.ASSIGNED: {Status.ARRIVED, Status.CANCELLED},
        Status.ARRIVED: {Status.ONGOING, Status.NO_SHOW, Status.CANCELLED},
        Status.ONGOING: {Status.COMPLETED},
    }

    def transition_to(self, new_status):
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Invalid transition {self.status} → {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    def cancel(self, *, by):
        if self.status in {self.Status.COMPLETED, self.Status.CANCELLED}:
            raise ValidationError("Ride cannot be cancelled")
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = by
        self.save(update_fields=[
            "status",
            "cancelled_at",
            "cancelled_by",
            "updated_at",
        ])

    def __str__(self):
        return f"Ride #{self.id} ({self.status})"

class RideFeedback(models.Model):
    ride = models.OneToOneField(
        Ride,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name="rating_between_1_and_5",
            )
        ]
