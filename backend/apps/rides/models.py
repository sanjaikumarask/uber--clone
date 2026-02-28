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
        ADMIN = "ADMIN"

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
    pickup_address = models.CharField(max_length=255, null=True, blank=True)
    drop_lat = models.FloatField()
    drop_lng = models.FloatField()
    drop_address = models.CharField(max_length=255, null=True, blank=True)

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
    actual_route_polyline = models.TextField(null=True, blank=True, help_text="Encoded polyline of the actual path taken")
    last_snapped_lat = models.FloatField(null=True, blank=True)
    last_snapped_lng = models.FloatField(null=True, blank=True)

    # --------------------
    # Ride Lifecycle Times
    # --------------------
    start_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Locked when ONGOING begins (OTP verified)"
    )
    start_lat = models.FloatField(
        null=True, blank=True,
        help_text="Driver GPS latitude at ride start"
    )
    start_lng = models.FloatField(
        null=True, blank=True,
        help_text="Driver GPS longitude at ride start"
    )
    end_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Locked when ride is COMPLETED"
    )

    # --------------------
    # Ride state
    # --------------------
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SEARCHING,
        db_index=True,
    )

    vehicle_type = models.CharField(
        max_length=16,
        default="go",
        help_text="The tier requested: moto, auto, go, xl",
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
    
    fare_breakdown = models.JSONField(
        null=True,
        blank=True,
        help_text="Immutable audit log snapshot of fare calculation (base, distance, surge, waiting, etc) at trip completion"
    )

    # --------------------
    # OTP / arrival
    # --------------------
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    city = models.CharField(max_length=100, default="Chennai", db_index=True)
    
    # --------------------
    # Offers & Payments
    # --------------------
    applied_offer = models.ForeignKey(
        "offers.Offer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rides"
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    driver_bonus = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    tip_amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal("0.00"),
        help_text="Tip added by rider AFTER payment. 100% goes to driver."
    )
    waiting_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Total seconds driver waited at pickup (arrived_at → otp_verified_at)"
    )

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
    is_fraud_flagged = models.BooleanField(
        default=False,
        help_text="Flagged if distance or waiting time is abnormally high compared to estimates."
    )


    ALLOWED_TRANSITIONS = {
        Status.SEARCHING: {Status.OFFERED, Status.ASSIGNED, Status.CANCELLED},
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

    @property
    def distance(self):
        return self.actual_distance_km or self.planned_distance_km or 0

class RideFeedback(models.Model):
    class GiverRole(models.TextChoices):
        RIDER = "RIDER", "Given by Rider"
        DRIVER = "DRIVER", "Given by Driver"

    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    giver_role = models.CharField(
        max_length=10,
        choices=GiverRole.choices,
        default=GiverRole.RIDER
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="driver_feedbacks",
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_feedbacks",
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One feedback per role per ride
        unique_together = ("ride", "giver_role")
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name="rating_between_1_and_5",
            )
        ]


class ChatMessage(models.Model):
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg from {self.sender} on Ride {self.ride_id}"
