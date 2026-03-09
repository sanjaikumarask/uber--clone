from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django_prometheus.models import ExportModelOperationsMixin


class Driver(ExportModelOperationsMixin("driver"), models.Model):
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

    class Level(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        ACTIVE = "ACTIVE", "Active"
        CONSISTENT = "CONSISTENT", "Consistent"
        PRO = "PRO", "Pro"

    level = models.CharField(
        max_length=16,
        choices=Level.choices,
        default=Level.NORMAL,
        db_index=True,
    )

    # Bank Details (for Payouts)
    bank_account_number = models.CharField(max_length=20, blank=True, default="")
    ifsc_code = models.CharField(max_length=11, blank=True, default="")

    # Vehicle Details
    vehicle_model = models.CharField(max_length=64, blank=True, default="")
    vehicle_number = models.CharField(max_length=20, blank=True, default="")

    is_verified = models.BooleanField(default=False)

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

    def __str__(self):
        return f"Driver #{self.id} ({self.status})"

    def transition_to(self, new_status):
        if not self.is_verified and new_status == self.Status.ONLINE:
            raise ValidationError("Unverified drivers cannot go ONLINE.")

        if new_status == self.status:
            return
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Invalid driver transition {self.status} -> {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])


class DriverDocument(models.Model):
    class Type(models.TextChoices):
        LICENSE = "LICENSE", "Driving License"
        RC = "RC", "Registration Certificate"
        INSURANCE = "INSURANCE", "Vehicle Insurance"
        AADHAAR = "AADHAAR", "National ID"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=20, choices=Type.choices)
    image = models.FileField(upload_to="driver_docs/", null=True, blank=True)
    file_path = models.CharField(max_length=255, blank=True, default="")  # Legacy/Backup
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    rejection_reason = models.TextField(blank=True, default="")

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_docs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def approve(self, admin_user):
        self.status = self.Status.APPROVED
        self.verified_by = admin_user
        self.save(update_fields=["status", "verified_by", "updated_at"])

        # Check if all required docs are approved to verify driver
        required = {self.Type.LICENSE, self.Type.RC, self.Type.INSURANCE}
        # Fetch status of all documents for this driver
        # We use a direct set of types that have APPROVED status
        approved = set(
            self.driver.documents.filter(status=self.Status.APPROVED).values_list(
                "document_type", flat=True
            )
        )

        print(f"[DEBUG] Driver {self.driver.id} documents: {approved}")
        print(f"[DEBUG] Required: {required}")

        from apps.notifications.models import Notification

        if required.issubset(approved):
            print(f"[DEBUG] Driver {self.driver.id} VERIFIED")
            self.driver.is_verified = True
            self.driver.save(update_fields=["is_verified"])

            # 🔥 Notify Driver: ACCOUNT VERIFIED
            Notification.objects.create(
                user=self.driver.user,
                channel="push",
                type="ACCOUNT_VERIFIED",
                payload={
                    "message": "Congratulations! Your profile has been verified. You can now go ONLINE."
                },
            )
        else:
            missing = required - approved
            print(f"[DEBUG] Driver {self.driver.id} still missing: {missing}")
            # Notify Document Approval
            Notification.objects.create(
                user=self.driver.user,
                channel="push",
                type="DOCUMENT_APPROVED",
                payload={
                    "document_type": self.document_type,
                    "message": f"Your {self.document_type} has been approved.",
                },
            )

    def reject(self, admin_user, reason):
        self.status = self.Status.REJECTED
        self.verified_by = admin_user
        self.rejection_reason = reason
        self.save(
            update_fields=["status", "verified_by", "rejection_reason", "updated_at"]
        )

        self.driver.is_verified = False
        self.driver.save(update_fields=["is_verified"])

        # ❌ Notify Driver: DOCUMENT REJECTED
        from apps.notifications.models import Notification

        Notification.objects.create(
            user=self.driver.user,
            channel="push",
            type="DOCUMENT_REJECTED",
            payload={
                "document_type": self.document_type,
                "reason": reason,
                "message": f"Your {self.document_type} was rejected: {reason}. Please re-upload.",
            },
        )


class DriverStats(models.Model):
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        related_name="stats",
    )

    total_rides = models.PositiveIntegerField(default=0)
    offered_rides = models.PositiveIntegerField(default=0)
    accepted_rides = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    cancelled_rides = models.PositiveIntegerField(default=0)
    no_shows = models.PositiveIntegerField(default=0)
    weekly_rides = models.PositiveIntegerField(default=0)
    peak_hour_rides = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0.0)

    # ------------------------------------------
    # Trust & Safety Scoring
    # ------------------------------------------
    fraud_flags_count = models.PositiveIntegerField(
        default=0, help_text="Total number of rides flagged for anomalous distance/time"
    )
    acceptance_rate = models.FloatField(
        default=100.0, help_text="Percentage of offered rides accepted (0-100)"
    )
    cancellation_rate = models.FloatField(
        default=0.0,
        help_text="Percentage of accepted rides cancelled by driver (0-100)",
    )
    trust_score = models.FloatField(
        default=100.0,
        help_text="Algorithmic reputation score. Drops upon fraud flags, cancellations.",
    )

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

    # ------------------------------------------
    # Admin Overrides & Inactivity
    # ------------------------------------------
    level_override_until = models.DateTimeField(
        null=True, blank=True, help_text="Manual level override expiry"
    )
    override_reason = models.TextField(blank=True, default="")
    last_active_at = models.DateTimeField(default=timezone.now)

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_level_overridden(self) -> bool:
        if not self.level_override_until:
            return False
        return self.level_override_until > timezone.now()

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
        self.save(
            update_fields=["rating_sum", "rating_count", "avg_rating", "updated_at"]
        )


class DriverLevelHistory(models.Model):
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name="level_history"
    )
    old_level = models.CharField(max_length=16, choices=Driver.Level.choices)
    new_level = models.CharField(max_length=16, choices=Driver.Level.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
