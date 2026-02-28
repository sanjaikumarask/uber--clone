from decimal import Decimal
from django.db.models import Sum

from apps.payments.models import LedgerEntry


ZERO = Decimal("0.00")


def get_wallet_balance(user) -> Decimal:
    """
    Total wallet balance:
    CREDIT - DEBIT
    (HOLD does NOT reduce wallet balance)
    """

    credits = (
        LedgerEntry.objects
        .filter(
            user=user,
            entry_type=LedgerEntry.Type.CREDIT,
        )
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    debits = (
        LedgerEntry.objects
        .filter(
            user=user,
            entry_type=LedgerEntry.Type.DEBIT,
        )
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    return credits - debits


def get_held_balance(user) -> Decimal:
    """
    Funds locked for payouts:
    HOLD - RELEASE
    """

    holds = (
        LedgerEntry.objects
        .filter(
            user=user,
            entry_type=LedgerEntry.Type.HOLD,
        )
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    releases = (
        LedgerEntry.objects
        .filter(
            user=user,
            entry_type=LedgerEntry.Type.RELEASE,
        )
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    return holds - releases


def get_available_balance(user) -> Decimal:
    """
    Spendable balance:
    wallet_balance - held_balance
    """

    return get_wallet_balance(user) - get_held_balance(user)
    
  
def debit_rider_wallet(user, amount: Decimal):
    """
    Deduct amount from rider wallet.
    Currently allows negative balance (credit line).
    """
    # In production, check balance > amount if prepaid.
    # Here we just record debit.
    LedgerEntry.objects.create(
        user=user,
        amount=amount,
        entry_type=LedgerEntry.Type.DEBIT,
        reason=LedgerEntry.Reason.PAYMENT,
    )


def credit_driver_wallet(driver, amount: Decimal):
    """
    Add earnings to driver wallet.
    """
    LedgerEntry.objects.create(
        user=driver.user, # Driver object passed, need user
        amount=amount,
        entry_type=LedgerEntry.Type.CREDIT,
        reason=LedgerEntry.Reason.DRIVER_EARNING,
    )
