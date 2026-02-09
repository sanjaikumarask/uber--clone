# apps/payments/services/payout.py
from decimal import Decimal
from django.db import transaction
from apps.payments.models import LedgerEntry
from apps.rides.fare_config import PLATFORM_COMMISSION_PERCENT


@transaction.atomic
def settle_driver_payout(*, ride, payment):
    total = payment.amount

    commission = (
        total * PLATFORM_COMMISSION_PERCENT / Decimal("100")
    ).quantize(Decimal("0.01"))

    driver_amount = total - commission

    # Platform commission
    LedgerEntry.objects.get_or_create(
        reference=f"commission:{payment.id}",
        defaults={
            "user": payment.user,
            "ride_id": ride.id,
            "amount": commission,
            "entry_type": LedgerEntry.Type.CREDIT,
            "reason": LedgerEntry.Reason.PLATFORM_COMMISSION,
        },
    )

    # Driver payout
    LedgerEntry.objects.get_or_create(
        reference=f"driver_payout:{payment.id}",
        defaults={
            "user": ride.driver.user,
            "ride_id": ride.id,
            "amount": driver_amount,
            "entry_type": LedgerEntry.Type.CREDIT,
            "reason": LedgerEntry.Reason.DRIVER_PAYOUT,
        },
    )
