from decimal import Decimal
from apps.payments.services.payout import (
    request_driver_payout,
)
from apps.payments.models import LedgerEntry, Payout


def test_driver_payout_request(driver_user):
    LedgerEntry.objects.create(
        user=driver_user,
        amount=Decimal("1000.00"),
        entry_type=LedgerEntry.Type.CREDIT,
        reason=LedgerEntry.Reason.DRIVER_EARNING,
    )

    payout = request_driver_payout(
        driver=driver_user,
        amount=Decimal("500.00"),
    )

    assert payout.status == Payout.Status.REQUESTED

    # HOLD exists
    assert LedgerEntry.objects.filter(
        user=driver_user,
        entry_type=LedgerEntry.Type.HOLD,
        reference__contains=payout.reference,
    ).exists()
