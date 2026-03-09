import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.payments.models import LedgerEntry, Payout
from apps.payments.services import ledger
from apps.payments.services.invariants import assert_user_ledger
from apps.payments.services.wallet import get_available_balance

WITHDRAWAL_FEE_PERCENT = Decimal("2.0")
logger = logging.getLogger(__name__)


def _platform_user():
    """
    Single system account that receives platform fees
    """
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    # Safely get or create to avoid DoesNotExist in tests/clean DBs
    user, _ = user_model.objects.get_or_create(
        id=settings.PLATFORM_USER_ID,
        defaults={"username": "platform_system_account", "role": "admin"},
    )
    return user


@transaction.atomic
def request_driver_payout(*, driver, amount: Decimal, reference=None) -> Payout:
    """
    Driver requests payout (REQUESTED)
    """

    amount = Decimal(amount).quantize(Decimal("0.01"))

    if amount <= 0:
        raise ValueError("Invalid payout amount")

    # ── CONCURRENCY LOCK (High Load Optimization) ──
    # At 10k+ users, multiple workers might process payouts for the same driver pool.
    # select_for_update() ensures strict consistency for the balance check.
    # Note: We do NOT use skip_locked here as we MUST be certain of the driver's
    # current balance and cannot skip/retry later for this specific flow.
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    # Log context for observability
    logger.info(
        f"[Payout] Acquiring financial lock for driver {driver.id}",
        extra={"driver_id": driver.id},
    )
    user_model.objects.select_for_update().get(id=driver.id)

    available = get_available_balance(driver)
    if amount > available:
        raise ValueError("Insufficient available balance")

    fee = (amount * WITHDRAWAL_FEE_PERCENT / 100).quantize(Decimal("0.01"))
    net = amount - fee

    # 🛑 CHECK DAILY LIMIT (₹50,000)
    DAILY_LIMIT = Decimal("50000.00")
    from django.db.models import Sum
    from django.utils import timezone

    today = timezone.now().date()

    # Sum all active payouts for today
    withdrawn_today = Payout.objects.filter(
        driver=driver, created_at__date=today
    ).exclude(status=Payout.Status.FAILED).aggregate(Sum("amount"))[
        "amount__sum"
    ] or Decimal(
        "0.00"
    )

    if withdrawn_today + amount > DAILY_LIMIT:
        remaining = max(DAILY_LIMIT - withdrawn_today, Decimal("0.00"))
        raise ValueError(f"Daily limit exceeded. Remaining limit: ₹{remaining}")

    if reference is None:
        reference = f"payout:{driver.id}:{payout_uuid()}"

    # ── IDEMPOTENCY CHECK ──
    # Ensure reference-based idempotency if one was provided
    existing_payout = Payout.objects.filter(reference=reference).first()
    if existing_payout:
        return existing_payout

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

    # ── IDEMPOTENCY GUARD ──
    # Ensure this ride payout hasn't already been processed
    if LedgerEntry.objects.filter(
        reference=f"earning:{ride.id}", reason=LedgerEntry.Reason.DRIVER_EARNING
    ).exists():
        return Decimal("0.00"), Decimal("0.00")

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
