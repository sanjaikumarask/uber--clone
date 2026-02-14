from celery import shared_task
from decimal import Decimal
from django.db import transaction
from django.conf import settings

from apps.drivers.models import Driver
from apps.payments.models import Payout
from apps.payments.services.wallet import get_available_balance
from apps.payments.services.payout import request_driver_payout
from apps.payments.services.payout_gateway import create_driver_payout

MIN_PAYOUT_AMOUNT = Decimal("500.00")


@shared_task
def trigger_scheduled_payouts():
    """
    Orchestrator: Finds eligible drivers and queues individual payouts.
    Scheduled: Daily @ 3 AM
    """
    # 1. Find active drivers
    active_drivers = Driver.objects.exclude(status=Driver.Status.BLOCKED).only('id', 'user')
    
    count = 0
    for driver in active_drivers:
        # Optimization: Pre-check balance to reduce queue noise
        if get_available_balance(driver.user) >= MIN_PAYOUT_AMOUNT:
            process_driver_payout.delay(driver.id)
            count += 1
            
    return f"Triggered payouts for {count} drivers"


@shared_task(
    bind=True, 
    max_retries=3, 
    soft_time_limit=30
)
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
                
                return f"Payout Failed: {str(e)}"

    except Exception as e:
        # Retry on network failures if needed
        # self.retry(exc=e, countdown=60)
        return f"Failed: {str(e)}"


@shared_task(
    bind=True,
    # autoretry_for=(Exception,), # REMOVED: We handle exceptions internally now
    # retry_kwargs={"max_retries": 5, "countdown": 60},
)
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
