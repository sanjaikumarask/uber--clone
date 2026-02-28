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

def reverse_ledger_entry(original_entry_id: int, admin_user) -> LedgerEntry:
    """
    IMMUTABLE AUDIT ROLLBACK:
    Never mutates or deletes the original row. Instead, calculates the exact inverse 
    operation (Credit -> Debit, Hold -> Release) and creates a new row with the `CORRECTION` flag,
    preserving the mathematical timeline of the ledger.
    """
    from django.db import transaction
    
    with transaction.atomic():
        entry = LedgerEntry.objects.select_for_update().get(id=original_entry_id)
        
        # Guard: Check if it's already been reversed to prevent double-refunds
        reverse_ref = f"reversal_for_{entry.id}"
        if LedgerEntry.objects.filter(reference=reverse_ref).exists():
            raise ValueError("This ledger entry has already been reversed.")
            
        inverse_type = {
            LedgerEntry.Type.CREDIT: LedgerEntry.Type.DEBIT,
            LedgerEntry.Type.DEBIT: LedgerEntry.Type.CREDIT,
            LedgerEntry.Type.HOLD: LedgerEntry.Type.RELEASE,
            LedgerEntry.Type.RELEASE: LedgerEntry.Type.HOLD,
        }[entry.entry_type]
        
        return _create_entry(
            user=entry.user,
            amount=entry.amount,
            entry_type=inverse_type,
            reference=reverse_ref,
            reason=LedgerEntry.Reason.CORRECTION,
            ride_id=entry.ride_id,
            payment=entry.payment,
        )
