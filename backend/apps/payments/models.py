from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django_prometheus.models import ExportModelOperationsMixin


class Payment(ExportModelOperationsMixin("payment"), models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED"
        AUTHORIZED = "AUTHORIZED"
        CAPTURED = "CAPTURED"
        FAILED = "FAILED"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
        REFUNDED = "REFUNDED"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    ride_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    currency = models.CharField(max_length=8, default="INR")

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )

    gateway = models.CharField(max_length=32, default="razorpay")
    gateway_order_id = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
    )
    gateway_payment_id = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
    )
    gateway_signature = models.CharField(
        max_length=256,
        blank=True,
        default="",
    )

    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        help_text="Network-edge idempotency tracking key",
    )

    failure_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["ride_id"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["ride_id"],
                condition=Q(status="CAPTURED"),
                name="one_captured_payment_per_ride",
            )
        ]

    @property
    def refundable_amount(self):
        return max(self.amount - self.refunded_amount, Decimal("0.00"))


class LedgerEntry(ExportModelOperationsMixin("ledger_entry"), models.Model):
    """
    IMMUTABLE ACCOUNTING LEDGER
    NEVER UPDATE — ONLY INSERT
    """

    class Type(models.TextChoices):
        CREDIT = "CREDIT"
        DEBIT = "DEBIT"
        HOLD = "HOLD"
        RELEASE = "RELEASE"

    class Reason(models.TextChoices):
        PAYMENT = "PAYMENT"
        DRIVER_EARNING = "DRIVER_EARNING"
        PLATFORM_COMMISSION = "PLATFORM_COMMISSION"
        DRIVER_PAYOUT = "DRIVER_PAYOUT"
        WITHDRAWAL_FEE = "WITHDRAWAL_FEE"
        REFUND = "REFUND"
        PENALTY = "PENALTY"
        INCENTIVE = "INCENTIVE"
        CORRECTION = "CORRECTION"
        OTHER = "OTHER"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )

    ride_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    payment = models.ForeignKey(
        Payment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries",
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    entry_type = models.CharField(
        max_length=10,
        choices=Type.choices,
        db_index=True,
    )

    reference = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        unique=True,
        help_text="Idempotency / correlation key",
    )

    reason = models.CharField(
        max_length=64,
        choices=Reason.choices,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["created_at"]


class Payout(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED"
        PROCESSING = "PROCESSING"
        PAID = "PAID"
        FAILED = "FAILED"

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payouts",
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )

    reference = models.CharField(
        max_length=128,
        unique=True,
    )

    gateway_payout_id = models.CharField(
        max_length=128, unique=True, null=True, blank=True
    )

    failure_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WebhookEvent(models.Model):
    """
    Persistent webhook idempotency + audit log.
    One row per gateway event.
    """

    gateway = models.CharField(
        max_length=32,
        default="razorpay",
        db_index=True,
    )

    event_id = models.CharField(
        max_length=128,
        unique=True,
        help_text="Gateway webhook event id",
    )

    event_type = models.CharField(
        max_length=64,
        db_index=True,
    )

    payload = models.JSONField()

    received_at = models.DateTimeField(auto_now_add=True)

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set once side-effects are applied",
    )

    status = models.CharField(
        max_length=16,
        default="RECEIVED",
        help_text="RECEIVED | PROCESSED | IGNORED | FAILED",
    )

    error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-received_at"]


class DriverEarnings(models.Model):
    driver = models.ForeignKey(
        "drivers.Driver",
        on_delete=models.CASCADE,
        related_name="earnings",
    )
    ride = models.OneToOneField(
        "rides.Ride",
        on_delete=models.CASCADE,
        related_name="earning",
    )
    # Total amount paid by rider
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Platform cut
    commission = models.DecimalField(max_digits=10, decimal_places=2)
    # What the driver actually gets
    net_earning = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Driver Earnings"
        ordering = ["-created_at"]
