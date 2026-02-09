from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.rides.models import Ride
from apps.payments.models import Payment, LedgerEntry


CANCEL_FEE_ASSIGNED = Decimal("25.00")


@transaction.atomic
def cancel_ride(*, ride: Ride, by: str):
    if ride.status in {Ride.Status.COMPLETED, Ride.Status.CANCELLED}:
        raise ValidationError("Ride cannot be cancelled")

    fee = Decimal("0.00")

    if by == Ride.CancelledBy.RIDER:
        if ride.status == Ride.Status.ASSIGNED:
            fee = CANCEL_FEE_ASSIGNED
        elif ride.status == Ride.Status.ARRIVED:
            raise ValidationError("Use NO_SHOW flow")

    ride.cancel(by=by)

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
