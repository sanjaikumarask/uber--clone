# apps/payments/services/invariants.py
from decimal import Decimal
from django.db.models import Sum

from apps.payments.models import LedgerEntry, Payout
from apps.payments.services.wallet import (
    get_wallet_balance,
    get_held_balance,
)


class LedgerInvariantError(RuntimeError):
    pass


def assert_wallet_invariants(user):
    """
    HARD GUARANTEES:
    - total >= 0
    - held >= 0
    - held <= total
    """

    total = get_wallet_balance(user)
    held = get_held_balance(user)

    if total < 0:
        raise LedgerInvariantError(
            f"NEGATIVE WALLET: user={user.id} total={total}"
        )

    if held < 0:
        raise LedgerInvariantError(
            f"NEGATIVE HOLD: user={user.id} held={held}"
        )

    if held > total:
        raise LedgerInvariantError(
            f"HOLD EXCEEDS BALANCE: user={user.id} held={held} total={total}"
        )


def assert_payout_backed_by_hold(payout: Payout):
    """
    Every payout MUST be backed by a HOLD entry of same amount
    """

    held = (
        LedgerEntry.objects.filter(
            user=payout.driver,
            entry_type=LedgerEntry.Type.HOLD,
            reference__icontains=payout.reference,
        )
        .aggregate(s=Sum("amount"))["s"]
        or Decimal("0.00")
    )

    if held != payout.amount:
        raise LedgerInvariantError(
            f"PAYOUT NOT BACKED BY HOLD: payout={payout.id} "
            f"expected={payout.amount} actual={held}"
        )


def assert_user_ledger(user):
    """
    One-call invariant check for a user
    """
    assert_wallet_invariants(user)

    payouts = Payout.objects.filter(driver=user)
    for payout in payouts:
        if payout.status in {
            Payout.Status.REQUESTED,
            Payout.Status.PROCESSING,
        }:
            assert_payout_backed_by_hold(payout)
