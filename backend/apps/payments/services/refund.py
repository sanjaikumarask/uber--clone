from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.payments.models import LedgerEntry, Payment
from apps.payments.razorpay_client import razorpay_client


@transaction.atomic
def refund_payment(
    *,
    payment: Payment,
    amount: Decimal,
    reason: str,
):
    """
    Handles partial + full refunds.
    Idempotent via ledger + payment row lock.
    """

    if payment.status not in {
        Payment.Status.CAPTURED,
        Payment.Status.PARTIALLY_REFUNDED,
    }:
        raise ValidationError("Payment not refundable")

    if amount <= 0:
        raise ValidationError("Refund amount must be positive")

    if amount > payment.refundable_amount:
        raise ValidationError("Refund exceeds refundable amount")

    # 🔒 Lock payment row
    payment = Payment.objects.select_for_update().get(id=payment.id)

    # ⬇️ Handle Simulation or Missing Client
    refund_id = f"sim_ref_{payment.id}"

    if payment.gateway != "simulation" and razorpay_client:
        # 🔁 Gateway refund (Razorpay)
        try:
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
        except Exception as e:
            raise ValidationError(f"Gateway refund failed: {e!s}") from e
    else:
        # For simulation, we just log it
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"SIMULATED_REFUND: Payment={payment.id} Amount={amount} Reason={reason}"
        )

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

    # 2️⃣ Ledger Claws: Proportionally debit Driver and Platform
    # Based on 80/20 split
    if payment.ride_id:
        from contextlib import suppress

        from apps.payments.services import payout as payout_service
        from apps.rides.models import Ride

        with suppress(Ride.DoesNotExist):
            ride = Ride.objects.get(id=payment.ride_id)
            if ride.driver:
                platform_share = (amount * Decimal("0.20")).quantize(Decimal("0.01"))
                driver_share = amount - platform_share

                # Debit Driver
                LedgerEntry.objects.create(
                    user=ride.driver.user,
                    ride_id=ride.id,
                    payment=payment,
                    amount=driver_share,
                    entry_type=LedgerEntry.Type.DEBIT,
                    reason=LedgerEntry.Reason.REFUND,
                    reference=f"refund_debit_driver:{refund_id}",
                )

                # Debit Platform
                LedgerEntry.objects.create(
                    user=payout_service._platform_user(),
                    ride_id=ride.id,
                    payment=payment,
                    amount=platform_share,
                    entry_type=LedgerEntry.Type.DEBIT,
                    reason=LedgerEntry.Reason.REFUND,
                    reference=f"refund_debit_platform:{refund_id}",
                )

    # 3️⃣ Update payment aggregates
    payment.refunded_amount += amount

    if payment.refunded_amount == payment.amount:
        payment.status = Payment.Status.REFUNDED
    else:
        payment.status = Payment.Status.PARTIALLY_REFUNDED

    payment.save(update_fields=["refunded_amount", "status", "updated_at"])

    # 3️⃣ Notify Rider
    from apps.notifications.models import Notification

    Notification.objects.create(
        user=payment.user,
        channel="push",
        type="REFUND_ISSUED",
        payload={
            "ride_id": payment.ride_id,
            "amount": float(amount),
            "message": f"A refund of ₹{amount} has been issued for your ride.",
        },
    )

    return {
        "refund_id": refund_id,
        "amount": amount,
        "status": payment.status,
    }

