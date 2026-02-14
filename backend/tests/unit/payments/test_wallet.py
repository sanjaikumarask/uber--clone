from decimal import Decimal
from apps.payments.models import LedgerEntry
from apps.payments.services.wallet import (
    get_wallet_balance,
    get_held_balance,
    get_available_balance,
)


def test_wallet_balance_calculation(user):
    # Credit 100
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("100.00"),
        entry_type=LedgerEntry.Type.CREDIT,
    )
    assert get_wallet_balance(user) == Decimal("100.00")

    # Debit 30
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("30.00"),
        entry_type=LedgerEntry.Type.DEBIT,
    )
    assert get_wallet_balance(user) == Decimal("70.00")


def test_held_balance_calculation(user):
    # Hold 50
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("50.00"),
        entry_type=LedgerEntry.Type.HOLD,
    )
    assert get_held_balance(user) == Decimal("50.00")

    # Release 20
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("20.00"),
        entry_type=LedgerEntry.Type.RELEASE,
    )
    assert get_held_balance(user) == Decimal("30.00")


def test_available_balance(user):
    # Wallet: 100 - 30 = 70
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("100.00"),
        entry_type=LedgerEntry.Type.CREDIT,
    )
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("30.00"),
        entry_type=LedgerEntry.Type.DEBIT,
    )

    # Held: 50 - 20 = 30
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("50.00"),
        entry_type=LedgerEntry.Type.HOLD,
    )
    LedgerEntry.objects.create(
        user=user,
        amount=Decimal("20.00"),
        entry_type=LedgerEntry.Type.RELEASE,
    )

    # Available: 70 - 30 = 40
    assert get_available_balance(user) == Decimal("40.00")
