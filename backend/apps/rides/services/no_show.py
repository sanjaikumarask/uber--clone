from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.rides.models import Ride
from apps.payments.models import Payment, LedgerEntry


NO_SHOW_FEE = Decimal("50.00")
NO_SHOW_DRIVER_PAYOUT = Decimal("40.00")


@transaction.atomic
def handle_no_show(*, ride: Ride):
    if ride.status != Ride.Status.ARRIVED:
        return

    ride.status = Ride.Status.NO_SHOW
    ride.no_show_marked_at = timezone.now()
    ride.save(update_fields=["status", "no_show_marked_at", "updated_at"])

    payment = Payment.objects.create(
        user=ride.rider,
        ride_id=ride.id,
        amount=NO_SHOW_FEE,
        status=Payment.Status.CAPTURED,
    )

    LedgerEntry.objects.create(
        user=ride.rider,
        ride_id=ride.id,
        payment=payment,
        amount=NO_SHOW_FEE,
        entry_type=LedgerEntry.Type.DEBIT,
        reference=f"no_show:{ride.id}",
        reason="no_show_fee",
    )

    LedgerEntry.objects.create(
        user=ride.driver.user,
        ride_id=ride.id,
        amount=NO_SHOW_DRIVER_PAYOUT,
        entry_type=LedgerEntry.Type.CREDIT,
        reference=f"no_show_payout:{ride.id}",
        reason="no_show_driver_payout",
    )
