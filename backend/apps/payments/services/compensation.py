from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.payments.models import LedgerEntry, Payment
from apps.drivers.models import Driver

@transaction.atomic
def compensate_driver(*, driver: Driver, ride_id: int, amount: Decimal, reason: str):
    """
    Adds a compensation credit to a driver's ledger.
    Used for cancellation fees or platform bonuses.
    """
    if amount <= 0:
        raise ValidationError("Compensation amount must be positive")

    # 1. Create Ledger Entry for Driver (CREDIT)
    LedgerEntry.objects.create(
        user=driver.user,
        ride_id=ride_id,
        amount=amount,
        entry_type=LedgerEntry.Type.CREDIT,
        reference=f"compensation:{ride_id}:{reason[:50]}",
        reason=LedgerEntry.Reason.INCENTIVE
    )

    # 2. Add to Driver Earning stats (optional but good for tracking)
    from apps.payments.models import DriverEarnings
    DriverEarnings.objects.create(
        driver=driver,
        ride_id=ride_id,
        amount=amount,
        commission=Decimal("0.00"),
        net_earning=amount
    )

    # 3. Notify Driver
    from apps.notifications.models import Notification
    Notification.objects.create(
        user=driver.user,
        channel="push",
        type="COMPENSATION_RECEIVED",
        payload={
            "ride_id": ride_id,
            "amount": float(amount),
            "message": f"You have received a compensation of ₹{amount}."
        }
    )

    return True
