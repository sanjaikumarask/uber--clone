from django.db import models
from django.conf import settings
from django.db.models import Q
from decimal import Decimal


class Payment(models.Model):
    """
    One payment attempt per ride.
    Multiple attempts allowed, only ONE can be CAPTURED.
    """

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        AUTHORIZED = "AUTHORIZED", "Authorized"
        CAPTURED = "CAPTURED", "Captured"
        FAILED = "FAILED", "Failed"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially Refunded"
        REFUNDED = "REFUNDED", "Refunded"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    # Keep as integer FK to avoid cross-app circular dependencies
    ride_id = models.PositiveBigIntegerField(
        db_index=True,
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    currency = models.CharField(
        max_length=8,
        default="INR",
    )

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )

    # =========================
    # GATEWAY METADATA
    # =========================

    gateway = models.CharField(
        max_length=32,
        default="razorpay",
    )

    gateway_order_id = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
    )

    gateway_payment_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )

    gateway_signature = models.CharField(
        max_length=256,
        null=True,
        blank=True,
    )

    failure_reason = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["ride_id"]),
            models.Index(fields=["gateway_order_id"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            # 🔒 HARD GUARANTEE: only one successful payment per ride
            models.UniqueConstraint(
                fields=["ride_id"],
                condition=Q(status="CAPTURED"),
                name="one_captured_payment_per_ride",
            )
        ]

    def __str__(self):
        return f"Payment #{self.id} {self.status} ₹{self.amount}"

    @property
    def refundable_amount(self) -> Decimal:
        return max(self.amount - self.refunded_amount, Decimal("0.00"))


class LedgerEntry(models.Model):
    """
    Immutable accounting ledger.
    NEVER update rows. Only INSERT.
    """

    class Type(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )

    ride_id = models.PositiveBigIntegerField(
        db_index=True,
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    entry_type = models.CharField(
        max_length=6,
        choices=Type.choices,
    )

    reference = models.CharField(
        max_length=128,
        help_text="payment:<id> | refund:<id> | adjustment:<id>",
    )

    # ✅ OPTIONAL — THIS FIXES YOUR MIGRATION ISSUE
    reason = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Optional human readable reason",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ride_id"]),
            models.Index(fields=["entry_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        sign = "-" if self.entry_type == self.Type.DEBIT else "+"
        return f"{sign}₹{self.amount} ride={self.ride_id}"
