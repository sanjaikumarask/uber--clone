from django.db.models import Sum, Case, When, DecimalField
from decimal import Decimal

from apps.payments.models import LedgerEntry


def get_wallet_balance(user) -> Decimal:
    """
    Wallet balance = SUM(CREDIT) - SUM(DEBIT)
    """

    agg = LedgerEntry.objects.filter(
        user=user
    ).aggregate(
        balance=Sum(
            Case(
                When(entry_type=LedgerEntry.Type.CREDIT, then="amount"),
                When(entry_type=LedgerEntry.Type.DEBIT, then=-1 * "amount"),
                default=0,
                output_field=DecimalField(),
            )
        )
    )

    return agg["balance"] or Decimal("0.00")
