from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.payments.models import LedgerEntry, Payment
from apps.rides.models import Ride

CANCEL_FEE_ASSIGNED = Decimal("25.00")
CANCEL_FEE_ARRIVED = Decimal("50.00")


@transaction.atomic
def cancel_ride(*, ride: Ride, by: str):
    if ride.status in {Ride.Status.COMPLETED, Ride.Status.CANCELLED}:
        raise ValidationError("Ride cannot be cancelled")

    fee = Decimal("0.00")

    if by == Ride.CancelledBy.RIDER:
        if ride.status == Ride.Status.ASSIGNED:
            fee = CANCEL_FEE_ASSIGNED
        elif ride.status == Ride.Status.ARRIVED:
            fee = CANCEL_FEE_ARRIVED

    ride.cancel(by=by)

    # 🚨 CRITICAL: Release the driver if there was one
    if ride.driver:
        from apps.drivers.models import Driver

        ride.driver.status = Driver.Status.ONLINE
        ride.driver.save(update_fields=["status"])

        # --- Trust Score Penalty for Driver Cancellations ---
        if by == Ride.CancelledBy.DRIVER:
            from apps.drivers.services.metrics import update_driver_metrics

            update_driver_metrics(ride.driver, "CANCELLED")

    # Broadcast cancellation
    from .lifecycle import _broadcast_status_update

    _broadcast_status_update(ride)

    # 📣 Notify Parties
    from apps.notifications.models import Notification

    # Notify Rider
    Notification.objects.create(
        user=ride.rider,
        channel="push",
        type="RIDE_CANCELLED",
        payload={
            "ride_id": ride.id,
            "message": f"Your ride has been cancelled by {by}.",
        },
    )

    # Notify Driver
    if ride.driver:
        Notification.objects.create(
            user=ride.driver.user,
            channel="push",
            type="RIDE_CANCELLED",
            payload={
                "ride_id": ride.id,
                "message": f"Trip #{ride.id} has been cancelled.",
            },
        )

    if fee > 0:
        payment = Payment.objects.create(
            user=ride.rider,
            ride_id=ride.id,
            amount=fee,
            status=Payment.Status.CAPTURED,
        )

        LedgerEntry.objects.create(
            user=ride.rider,
            ride_id=ride.id,
            payment=payment,
            amount=fee,
            entry_type=LedgerEntry.Type.DEBIT,
            reference=f"cancel:{ride.id}",
            reason="rider_cancellation_fee",
        )
