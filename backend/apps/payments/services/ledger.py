from decimal import Decimal
from apps.payments.models import LedgerEntry


def credit(user, ride_id, amount, reference):
    LedgerEntry.objects.create(
        user=user,
        ride_id=ride_id,
        amount=Decimal(amount),
        entry_type=LedgerEntry.Type.CREDIT,
        reference=reference,
    )


def debit(user, ride_id, amount, reference):
    LedgerEntry.objects.create(
        user=user,
        ride_id=ride_id,
        amount=Decimal(amount),
        entry_type=LedgerEntry.Type.DEBIT,
        reference=reference,
    )
