from decimal import Decimal
from django.db import IntegrityError
from apps.payments.models import LedgerEntry


def _create_entry(**kwargs):
    try:
        return LedgerEntry.objects.create(**kwargs)
    except IntegrityError:
        # Idempotent: entry already exists
        return LedgerEntry.objects.get(reference=kwargs["reference"])


def credit(*, user, amount, reference, reason, ride_id=None, payment=None):
    return _create_entry(
        user=user,
        amount=Decimal(amount),
        entry_type=LedgerEntry.Type.CREDIT,
        reference=reference,
        reason=reason,
        ride_id=ride_id,
        payment=payment,
    )


def debit(*, user, amount, reference, reason):
    return _create_entry(
        user=user,
        amount=Decimal(amount),
        entry_type=LedgerEntry.Type.DEBIT,
        reference=reference,
        reason=reason,
    )


def hold(*, user, amount, reference, reason):
    return _create_entry(
        user=user,
        amount=Decimal(amount),
        entry_type=LedgerEntry.Type.HOLD,
        reference=reference,
        reason=reason,
    )


def release_hold(*, user, amount, reference, reason):
    return _create_entry(
        user=user,
        amount=Decimal(amount),
        entry_type=LedgerEntry.Type.RELEASE,
        reference=reference,
        reason=reason,
    )
