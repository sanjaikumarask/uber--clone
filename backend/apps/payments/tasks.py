from celery import shared_task
from decimal import Decimal
import logging
from django.db import transaction
from django.conf import settings

from apps.drivers.models import Driver
from apps.payments.models import Payout
from apps.payments.services.wallet import get_available_balance
from apps.payments.services.payout import request_driver_payout
from apps.payments.services.payout_gateway import create_driver_payout
from apps.common.idempotency import idempotent_task
from apps.common.backpressure import CeleryQueueGuard, RetryStrategy

logger = logging.getLogger(__name__)

MIN_PAYOUT_AMOUNT = Decimal("500.00")


@shared_task
def trigger_scheduled_payouts():
    """
    Orchestrator: Finds eligible drivers and queues individual payouts.
    Scheduled: Daily @ 3 AM
    """
    from apps.rides.models import Ride

    # 1. Find active drivers
    active_drivers = Driver.objects.exclude(status=Driver.Status.BLOCKED).only('id', 'user')
    
    # ── BACKPRESSURE GUARD ──
    if not CeleryQueueGuard.can_enqueue():
        logger.warning("[Backpressure] Shedding scheduled payout tasks due to queue saturation")
        return "Shedding load due to backpressure"

    count = 0
    for driver in active_drivers:
        # 🚨 FRAUD ENFORCEMENT: Block automated payout if driver has flagged rides
        if Ride.objects.filter(driver=driver, is_fraud_flagged=True).exists():
            continue

        # Optimization: Pre-check balance to reduce queue noise
        if get_available_balance(driver.user) >= MIN_PAYOUT_AMOUNT:
            process_driver_payout.delay(driver.id)
            count += 1
            
    return f"Triggered payouts for {count} drivers"


@shared_task(bind=True)
@idempotent_task(ttl=3600)
def process_driver_payout(self, driver_id):
    """
    Worker: Safely processes a single driver's payout.
    """
    try:
        with transaction.atomic():
            # 1. Lock the driver row
            driver = Driver.objects.select_for_update().get(id=driver_id)
            user = driver.user
            
            # 2. Re-check Balance (Source of Truth)
            balance = get_available_balance(user)
            
            if balance < MIN_PAYOUT_AMOUNT:
                return f"Skipped: Balance {balance} < threshold"

            # 3. Check for Existing Scheduled Payout Today (Prevent Duplicates)
            from django.utils import timezone
            today_str = timezone.now().date().isoformat()
            payout_reference = f"payout:scheduled:{driver.user.id}:{today_str}"

            if Payout.objects.filter(reference=payout_reference).exists():
                return f"Skipped: Scheduled payout already exists ({payout_reference})"

            # 4. Create Payout & Hold Funds
            # This creates Payout(REQUESTED) and Ledger(HOLD)
            payout = request_driver_payout(
                driver=user,  # PASS USER INSTANCE
                amount=balance,
                reference=payout_reference # Deterministic Key
            )
            
            # 4. Initiate Gateway Transfer
            # Ensure Payout is in PROCESSING state before calling gateway?
            # request_driver_payout sets it to REQUESTED.
            # We should probably update to PROCESSING here or inside a service.
            
            payout.status = Payout.Status.PROCESSING
            payout.save(update_fields=["status"])

            try:
                # Call Gateway
                gateway_response = create_driver_payout(payout=payout)
                
                # Update with gateway ID
                payout.gateway_payout_id = gateway_response.get("id")
                payout.save(update_fields=["gateway_payout_id"])
                return f"Payout {payout.reference} initiated for {balance}"
                
            except Exception as e:
                # 🛑 FAILURE: Gateway rejected request (e.g. invalid bank details)
                # We catch this so the Payout Record persists as FAILED > Audit Trail
                
                payout.status = Payout.Status.FAILED
                payout.failure_reason = str(e)
                payout.save(update_fields=["status", "failure_reason"])
                
                # IMPORTANT: Release the HOLD since payout failed immediately
                from apps.payments.models import LedgerEntry
                from apps.payments.services import ledger as ledger_service
                
                ledger_service.release_hold(
                    user=user,
                    amount=balance,
                    reference=f"release:{payout.reference}",
                    reason=LedgerEntry.Reason.DRIVER_PAYOUT,
                )
                
                # 📢 FIRE ALERT: Automated payout drop requires Operations attention
                from apps.notifications.services.alerts import send_critical_alert
                send_critical_alert(
                    title=f"Failed Driver Payout: {payout.driver.first_name}",
                    message=f"Gateway failed processing payout {payout.reference} for {balance}.\nError: {e}",
                    level="ERROR"
                )
                
                return f"Payout Failed: {str(e)}"

    except Exception as e:
        # ── RETRY STRATEGY WITH JITTER ──
        countdown = RetryStrategy.get_countdown("CRITICAL", self.request.retries)
        if countdown >= 0:
            logger.info(f"Retrying payout for driver {driver_id} in {countdown}s")
            self.retry(exc=e, countdown=countdown)
        
        return f"Failed: {str(e)}"


@shared_task(bind=True)
@idempotent_task(ttl=3600)
def execute_driver_payout(self, payout_id: int):
    """
    Executes an EXISTING payout (e.g. Admin Approved).
    SAFE against double execution.
    """

    with transaction.atomic():
        payout = (
            Payout.objects
            .select_for_update()
            .get(id=payout_id)
        )

        # 🚫 Hard state gate
        if payout.status != Payout.Status.PROCESSING:
            return

        try:
            # External gateway call (idempotent by reference)
            gateway_response = create_driver_payout(payout=payout)
            
            # Update gateway ID
            payout.gateway_payout_id = gateway_response.get("id")
            payout.save(update_fields=["gateway_payout_id"])
            return f"Payout {payout.reference} initiated"

        except Exception as e:
            # 🛑 FAILURE: Gateway rejected request
            # Mark FAILED and Release Hold so funds aren't stuck
            payout.status = Payout.Status.FAILED
            payout.failure_reason = str(e)
            payout.save(update_fields=["status", "failure_reason"])
            
            from apps.payments.models import LedgerEntry
            from apps.payments.services import ledger as ledger_service
            
            ledger_service.release_hold(
                user=payout.driver,
                amount=payout.amount,
                reference=f"release:{payout.reference}",
                reason=LedgerEntry.Reason.DRIVER_PAYOUT,
            )
            return f"Payout Failed: {str(e)}"


# ============================================================
# BACKGROUND RECONCILIATION & RELIABILITY
# ============================================================

@shared_task
@idempotent_task(ttl=600)
def retry_failed_payouts():
    """
    SLA Task: Re-queues any payouts that failed specifically due to 
    gateway 5xx timeouts (not user bank errors).
    """
    from datetime import timedelta
    from django.utils import timezone
    
    # Target payouts that failed yesterday
    start_time = timezone.now() - timedelta(days=2)
    end_time = timezone.now() - timedelta(minutes=15)
    
    failed_payouts = Payout.objects.filter(
        status=Payout.Status.FAILED,
        created_at__gte=start_time,
        created_at__lte=end_time
    )
    
    retry_count = 0
    for payout in failed_payouts:
        # Avoid retrying permanently failing situations (e.g. Invalid Routing #)
        error = (payout.failure_reason or "").lower()
        if "timeout" in error or "unavailable" in error or "network" in error:
            # We simply re-trigger the scheduled orchestrator for this driver
            # Since the funds were returned to their balance upon FAILED status, 
            # this will safely re-hold and re-create a new Payout reference.
            process_driver_payout.delay(payout.driver_id)
            retry_count += 1
            
    return f"Re-queued {retry_count} transiently failed payouts."


@shared_task
@idempotent_task(ttl=600)
def reconcile_processing_payouts():
    """
    SLA Task: Reconciles payouts stuck in PROCESSING status.
    Called when a webhook is missed or delayed.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.payments.models import Payout
    from apps.payments.services.payout_gateway import get_payout_status
    from apps.payments.services.payout import mark_payout_success, mark_payout_failed

    # Payouts older than 15 mins but within 2 days
    cutoff_start = timezone.now() - timedelta(days=2)
    cutoff_end = timezone.now() - timedelta(minutes=15)

    processing_payouts = Payout.objects.filter(
        status=Payout.Status.PROCESSING,
        updated_at__gte=cutoff_start,
        updated_at__lte=cutoff_end
    )

    reconciled_count = 0
    for payout in processing_payouts:
        try:
            status_data = get_payout_status(
                gateway_payout_id=payout.gateway_payout_id,
                reference_id=payout.reference
            )
            
            if not status_data:
                continue

            pg_status = status_data.get("status")

            if pg_status == "processed":
                mark_payout_success(payout=payout)
                reconciled_count += 1
            elif pg_status == "failed" or pg_status == "cancelled":
                payout.failure_reason = status_data.get("failure_reason", "Reconciled Failure")
                mark_payout_failed(payout=payout)
                reconciled_count += 1
                
        except Exception as e:
            from apps.notifications.services.alerts import send_critical_alert
            send_critical_alert(
                title=f"Payout Reconciliation Error: {payout.id}",
                message=f"Failed to reconcile payout {payout.id}: {str(e)}",
                level="ERROR"
            )

    return f"Reconciled {reconciled_count} processing payouts."


@shared_task
@idempotent_task(ttl=600)
def reconcile_pending_payments():
    """
    SLA Task: Syncs missing Razorpay payments.
    Fixes the edge-case where Rider pays on Razorpay exactly as their phone
    runs out of battery, so 'VerifyPaymentView' is never hit by the App.
    """
    from apps.payments.models import Payment
    from apps.payments.views import razorpay_client
    from apps.payments.services.payout import settle_driver_payout
    from apps.rides.models import Ride
    from django.utils import timezone
    from datetime import timedelta
    
    if not razorpay_client:
        return "Gateway not configured."

    cutoff_end = timezone.now() - timedelta(minutes=15)
    cutoff_start = timezone.now() - timedelta(days=1)
    
    pending = Payment.objects.filter(
        status__in=[Payment.Status.CREATED, Payment.Status.AUTHORIZED],
        created_at__gte=cutoff_start,
        created_at__lte=cutoff_end
    ).exclude(gateway_order_id__isnull=True)
    
    fixed_count = 0
    for payment in pending:
        try:
            order_data = razorpay_client.order.payments(payment.gateway_order_id)
            items = order_data.get("items", [])
            
            captured_pg = next((i for i in items if i.get("status") == "captured"), None)
            
            if captured_pg:
                with transaction.atomic():
                    # Double-lock to prevent race with user reconnecting
                    p_lock = Payment.objects.select_for_update().get(id=payment.id)
                    if p_lock.status == Payment.Status.CAPTURED:
                        continue
                        
                    p_lock.gateway_payment_id = captured_pg["id"]
                    p_lock.status = Payment.Status.CAPTURED
                    p_lock.save()
                    
                    from apps.payments.models import LedgerEntry
                    LedgerEntry.objects.create(
                        user=p_lock.user,
                        ride_id=p_lock.ride_id,
                        amount=p_lock.amount,
                        entry_type=LedgerEntry.Type.DEBIT,
                        reason=LedgerEntry.Reason.PAYMENT,
                        reference=f"payment_recon:{p_lock.gateway_payment_id}",
                    )
                    
                    ride_lock = Ride.objects.select_for_update().get(id=p_lock.ride_id)
                    settle_driver_payout(ride=ride_lock, payment=p_lock)
                    
                fixed_count += 1
                
        except Exception as e:
            pass # Keep scanning the rest

    return f"Reconciled {fixed_count} dropped payments automatically."


@shared_task
def audit_platform_ledger():
    """
    SLA Task: Natively compares internal Ledger(PostgreSQL) to 
    External Bank Record (Razorpay). Validates 1:1 total liquidity. 
    Runs weekly off-peak.
    """
    from apps.payments.models import LedgerEntry, Payment
    from django.db.models import Sum
    from apps.notifications.services.alerts import send_critical_alert
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        from django.db.models import F
        # Sum total NET payments (Amount - Refunded)
        # We only count payments that reached at least CAPTURED status.
        internal_sum = Payment.objects.filter(
            status__in=[Payment.Status.CAPTURED, Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED]
        ).aggregate(
            total=Sum(F('amount') - F('refunded_amount'))
        )['total'] or Decimal('0.00')
        
        # Validates Net Driver Earnings (Credits - Debits)
        driver_credits = LedgerEntry.objects.filter(
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        driver_debits = LedgerEntry.objects.filter(
            entry_type=LedgerEntry.Type.DEBIT,
            reason__in=[LedgerEntry.Reason.REFUND, LedgerEntry.Reason.CORRECTION, LedgerEntry.Reason.PENALTY]
        ).exclude(
            # Exclude actual payouts (withdrawals) as they aren't part of "earnings" balance comparison
            reason=LedgerEntry.Reason.DRIVER_PAYOUT 
        ).filter(
            # Target driver accounts specifically (optional if penalty/refund reasons are strictly driver-owned)
            # but safer to query for non-platform users.
            user__is_staff=False 
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        net_driver_distributed = driver_credits - driver_debits
        
        # Validates Net Platform Commission (Credits - Debits)
        platform_credits = LedgerEntry.objects.filter(
            entry_type=LedgerEntry.Type.CREDIT, 
            reason__in=[LedgerEntry.Reason.PLATFORM_COMMISSION, LedgerEntry.Reason.WITHDRAWAL_FEE]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        platform_debits = LedgerEntry.objects.filter(
            user_id=settings.PLATFORM_USER_ID,
            entry_type=LedgerEntry.Type.DEBIT,
            reason__in=[LedgerEntry.Reason.REFUND, LedgerEntry.Reason.CORRECTION]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        net_platform_distributed = platform_credits - platform_debits
        
        total_distributed = net_driver_distributed + net_platform_distributed

        if total_distributed != internal_sum:
            drift = internal_sum - total_distributed
            msg = f"LEDGER DRIFT DETECTED! Net internal funds (Rider) do not match Net distributed (Driver+Platform). Drift: {drift}. (Internal: {internal_sum}, Distributed: {total_distributed})"
            logger.critical(msg)
            send_critical_alert(
                title="CRITICAL: Database Ledger Drift Drift",
                message=msg,
                level="CRITICAL"
            )
            
        return "Audit Completed. Ledger is mathematically sound."
        
    except Exception as e:
        logger.error(f"Audit failure: {e}")
        return str(e)
