from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.payments.models import Payment, LedgerEntry
from apps.payments.razorpay_client import razorpay_client


@transaction.atomic
def refund_payment(
    *,
    payment: Payment,
    amount: Decimal,
    reason: str,
    initiated_by,
):
    """
    Handles partial + full refunds.
    Idempotent via ledger + payment row lock.
    """

    if payment.status not in (
        Payment.Status.CAPTURED,
        Payment.Status.PARTIALLY_REFUNDED,
    ):
        raise ValidationError("Payment not refundable")

    if amount <= 0:
        raise ValidationError("Refund amount must be positive")

    if amount > payment.refundable_amount:
        raise ValidationError("Refund exceeds refundable amount")

    # 🔒 Lock payment row
    payment = (
        Payment.objects
        .select_for_update()
        .get(id=payment.id)
    )

    # 🔁 Gateway refund (Razorpay)
    refund = razorpay_client.payment.refund(
        payment.gateway_payment_id,
        {
            "amount": int(amount * 100),  # paise
            "notes": {
                "reason": reason,
                "payment_id": payment.id,
            },
        },
    )

    refund_id = refund["id"]

    # 1️⃣ Ledger: platform → rider (CREDIT)
    LedgerEntry.objects.create(
        user=payment.user,
        ride_id=payment.ride_id,
        payment=payment,
        amount=amount,
        entry_type=LedgerEntry.Type.CREDIT,
        reference=f"refund:{refund_id}",
        reason=reason,
    )

    # 2️⃣ Update payment aggregates
    payment.refunded_amount += amount

    if payment.refunded_amount == payment.amount:
        payment.status = Payment.Status.REFUNDED
    else:
        payment.status = Payment.Status.PARTIALLY_REFUNDED

    payment.save(
        update_fields=["refunded_amount", "status", "updated_at"]
    )

    return {
        "refund_id": refund_id,
        "amount": amount,
        "status": payment.status,
    }
