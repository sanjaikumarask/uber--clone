from decimal import Decimal
from django.db import transaction
from django.conf import settings

from apps.payments.models import Payout, LedgerEntry
from apps.payments.services import ledger
from apps.payments.services.wallet import get_available_balance
from apps.payments.services.invariants import assert_user_ledger

WITHDRAWAL_FEE_PERCENT = Decimal("2.0")


def _platform_user():
    """
    Single system account that receives platform fees
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.get(id=settings.PLATFORM_USER_ID)


@transaction.atomic
def request_driver_payout(*, driver, amount: Decimal, reference=None) -> Payout:
    """
    Driver requests payout (REQUESTED)
    """

    amount = Decimal(amount).quantize(Decimal("0.01"))

    if amount <= 0:
        raise ValueError("Invalid payout amount")

    available = get_available_balance(driver)
    if amount > available:
        raise ValueError("Insufficient available balance")

    fee = (amount * WITHDRAWAL_FEE_PERCENT / 100).quantize(Decimal("0.01"))
    net = amount - fee

    # 🛑 CHECK DAILY LIMIT (₹50,000)
    DAILY_LIMIT = Decimal("50000.00")
    from django.utils import timezone
    from django.db.models import Sum

    today = timezone.now().date()
    
    # Sum all active payouts for today
    withdrawn_today = Payout.objects.filter(
        driver=driver,
        created_at__date=today
    ).exclude(
        status=Payout.Status.FAILED
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")

    if withdrawn_today + amount > DAILY_LIMIT:
        remaining = max(DAILY_LIMIT - withdrawn_today, Decimal("0.00"))
        raise ValueError(f"Daily limit exceeded. Remaining limit: ₹{remaining}")

    if reference is None:
        reference = f"payout:{driver.id}:{payout_uuid()}"

    payout = Payout.objects.create(
        driver=driver,
        amount=amount,
        fee=fee,
        net_amount=net,
        status=Payout.Status.REQUESTED,
        reference=reference,
    )

    ledger.hold(
        user=driver,
        amount=amount,
        reference=f"hold:{payout.reference}",
        reason=LedgerEntry.Reason.DRIVER_PAYOUT,
    )

    assert_user_ledger(driver)
    return payout


@transaction.atomic
def mark_payout_success(*, payout: Payout):
    """
    Gateway SUCCESS webhook
    """

    if payout.status == Payout.Status.PAID:
        return payout

    if payout.status != Payout.Status.PROCESSING:
        raise ValueError("Payout not in PROCESSING state")

    # 1️⃣ Release hold
    ledger.release_hold(
        user=payout.driver,
        amount=payout.amount,
        reference=f"release:{payout.reference}",
        reason=LedgerEntry.Reason.DRIVER_PAYOUT,
    )

    # 2️⃣ Final debit
    ledger.debit(
        user=payout.driver,
        amount=payout.amount,
        reference=f"debit:{payout.reference}",
        reason=LedgerEntry.Reason.DRIVER_PAYOUT,
    )

    # 3️⃣ Platform fee
    ledger.credit(
        user=_platform_user(),
        amount=payout.fee,
        reference=f"fee:{payout.reference}",
        reason=LedgerEntry.Reason.WITHDRAWAL_FEE,
    )

    payout.status = Payout.Status.PAID
    payout.save(update_fields=["status"])

    assert_user_ledger(payout.driver)
    return payout


@transaction.atomic
def mark_payout_failed(*, payout: Payout):
    """
    Gateway FAILED webhook
    """

    if payout.status in {Payout.Status.FAILED, Payout.Status.PAID}:
        return payout

    ledger.release_hold(
        user=payout.driver,
        amount=payout.amount,
        reference=f"release:{payout.reference}",
        reason=LedgerEntry.Reason.DRIVER_PAYOUT,
    )

    payout.status = Payout.Status.FAILED
    payout.save(update_fields=["status"])

    assert_user_ledger(payout.driver)
    return payout


@transaction.atomic
def settle_driver_payout(*, ride, payment):
    """
    Distributes funds AFTER payment is CAPTURED.
    CREDIT Driver wallet
    CREDIT Platform wallet (commission)
    """
    if payment.status != "CAPTURED":
        raise ValueError("Payment not captured")

    # 1. Calculate splits (80/20)
    total = payment.amount
    platform_fee = (total * Decimal("0.20")).quantize(Decimal("0.01"))
    driver_amount = total - platform_fee

    # 2. Credit Driver
    ledger.credit(
        user=ride.driver.user,
        amount=driver_amount,
        reference=f"earning:{ride.id}",
        reason=LedgerEntry.Reason.DRIVER_EARNING,
        ride_id=ride.id,
        payment=payment,
    )

    # 3. Credit Platform
    ledger.credit(
        user=_platform_user(),
        amount=platform_fee,
        reference=f"commission:{ride.id}",
        reason=LedgerEntry.Reason.PLATFORM_COMMISSION,
        ride_id=ride.id,
        payment=payment,
    )

    return driver_amount, platform_fee


def payout_uuid():
    import uuid
    return uuid.uuid4().hex
