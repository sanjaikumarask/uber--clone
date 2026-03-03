import logging
import time
from django.db import transaction
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

# Mocking external client if not imported logic
from apps.payments.views import razorpay_client
from apps.payments.services.payout_gateway import get_payout_status
from apps.payments.services.payout import mark_payout_success, mark_payout_failed
from apps.payments.models import Payout, Payment
from apps.rides.models import Ride

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def reconcile_payout_status_task(self, payout_id):
    """
    Individual Payout Reconciliation.
    Triggered when a webhook is delayed or 
    by the periodic scanner.
    """
    try:
        payout = Payout.objects.get(id=payout_id)
        if payout.status != Payout.Status.PROCESSING:
            return f"Payout {payout_id} not in PROCESSING"

        # 1. Fetch from Gateway
        status_data = get_payout_status(
            gateway_payout_id=payout.gateway_payout_id,
            reference_id=payout.reference
        )

        if not status_data:
            return f"No data for {payout_id}"

        pg_status = status_data.get("status")

        # 2. Reconcile states
        if pg_status == "processed":
            mark_payout_success(payout=payout)
        elif pg_status in ["failed", "rejected", "cancelled"]:
            payout.failure_reason = status_data.get("failure_reason", "Gateway Failure")
            mark_payout_failed(payout=payout)
        
        return f"Reconciled {payout_id} to {pg_status}"

    except Exception as exc:
        logger.error(f"Reconciliation failed for Payout {payout_id}: {exc}", extra={"payout_id": payout_id})
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task
def global_payout_reconciliation_scanner():
    """
    Periodic job to find 'Stuck' payouts.
    """
    cutoff = timezone.now() - timedelta(minutes=30)
    stuck_payouts = Payout.objects.filter(
        status=Payout.Status.PROCESSING,
        updated_at__lt=cutoff
    ).values_list('id', flat=True)

    for p_id in stuck_payouts:
        reconcile_payout_status_task.delay(p_id)
    
    return f"Queued {len(stuck_payouts)} payouts for reconciliation"
