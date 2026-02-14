from decimal import Decimal
from django.db.models import Sum
from apps.payments.models import LedgerEntry


class LedgerViolation(Exception):
    pass


def _sum(user, entry_type):
    return (
        LedgerEntry.objects
        .filter(user=user, entry_type=entry_type)
        .aggregate(s=Sum("amount"))["s"]
        or Decimal("0.00")
    )


def verify_user_ledger(user):
    credit = _sum(user, LedgerEntry.Type.CREDIT)
    debit = _sum(user, LedgerEntry.Type.DEBIT)

    hold = _sum(user, LedgerEntry.Type.HOLD)
    release = _sum(user, LedgerEntry.Type.RELEASE)

    total = credit - debit
    held = hold - release
    available = total - held

    if credit < 0 or debit < 0:
        raise LedgerViolation("Negative credit/debit")

    if held < 0:
        raise LedgerViolation("Negative held balance")

    if total < 0:
        raise LedgerViolation("Negative total balance")

    if available < 0:
        raise LedgerViolation("Negative available balance")

    return {
        "credit": credit,
        "debit": debit,
        "held": held,
        "total": total,
        "available": available,
    }
