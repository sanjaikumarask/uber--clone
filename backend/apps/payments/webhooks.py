import hashlib
import hmac
import json
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.common.idempotency import idempotent_webhook
from apps.payments.models import LedgerEntry, Payment, Payout
from apps.payments.services.payout import (
    mark_payout_failed,
    mark_payout_success,
)
from apps.payments.services.razorpay import verify_razorpay_payout_webhook
from apps.payments.services.webhooks import register_webhook_event


# =====================================================
# PAYMENT WEBHOOK SIGNATURE VERIFY
# =====================================================
def _verify_payment_webhook(*, body: bytes, signature: str) -> bool:
    # [SECURITY AUDIT] Fail-safe check for secret presence
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
    if not secret:
        import logging
        logging.getLogger(__name__).critical("RAZORPAY_WEBHOOK_SECRET missing")
        return False

    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ==============================
# PAYMENT (RIDE PAYMENT) WEBHOOK
# ==============================
# [SECURITY AUDIT] CSRF exemption is safe here because we perform mandatory 
# HMAC-SHA256 signature verification. This ensures the request is genuine 
# from Razorpay and prevents CSRF/forgery attacks.
@csrf_exempt
@require_POST
@idempotent_webhook("razorpay")
def razorpay_webhook(request):
    signature = request.headers.get("X-Razorpay-Signature")
    body = request.body

    # [SECURITY AUDIT] Ensure webhook secret is configured before attempting verification
    if not getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None):
        import logging
        logging.getLogger(__name__).critical("RAZORPAY_WEBHOOK_SECRET missing")
        return HttpResponse(status=500)

    if not signature or not _verify_payment_webhook(body=body, signature=signature):
        return HttpResponse(status=400)

    data = json.loads(body)

    event_id = data.get("id")
    event_type = data.get("event")

    if event_type != "payment.captured":
        return HttpResponse(status=200)

    # 🔒 IDENTITY GATE
    if not register_webhook_event(
        provider="razorpay",
        event_id=event_id,
        event_type=event_type,
        raw_body=body,
    ):
        return HttpResponse(status=200)

    payment_entity = data["payload"]["payment"]["entity"]
    order_id = payment_entity["order_id"]
    payment_id = payment_entity["id"]
    amount = Decimal(payment_entity["amount"]) / Decimal("100")

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .filter(gateway_order_id=order_id)
            .first()
        )

        if not payment or payment.status == Payment.Status.CAPTURED:
            return HttpResponse(status=200)

        payment.status = Payment.Status.CAPTURED
        payment.gateway_payment_id = payment_id
        payment.save(update_fields=["status", "gateway_payment_id"])

        LedgerEntry.objects.create(
            user=payment.user,
            ride_id=payment.ride_id,
            amount=amount,
            entry_type=LedgerEntry.Type.DEBIT,
            reference=f"payment:{payment.id}",
            reason=LedgerEntry.Reason.PAYMENT,
        )

        # Ensure Driver Gets Paid if Webhook wins the race condition
        try:
            from apps.payments.services.payout import settle_driver_payout
            from apps.rides.models import Ride

            ride = Ride.objects.select_for_update().get(id=payment.ride_id)
            settle_driver_payout(ride=ride, payment=payment)
        except Exception:
            # Note: We don't fail the webhook if payout errors; retry payout separately.
            pass

        from apps.notifications.models import Notification

        transaction.on_commit(
            lambda: Notification.objects.create(
                user=payment.user,
                channel="email",
                type="PAYMENT_CONFIRMED",
                payload={
                    "subject": f"Payment Successful - Ride #{payment.ride_id}",
                    "body": f"Hi {payment.user.first_name}, your payment of ₹{payment.amount} was successful. Trans ID: {payment.gateway_payment_id}",
                    "html": f"<h2>Payment Successful ✅</h2><p>Your payment of <strong>₹{payment.amount}</strong> has been received for ride #{payment.ride_id}.</p><p>Transaction ID: {payment.gateway_payment_id}</p>",
                },
            )
        )

    return HttpResponse(status=200)


# ==============================
# PAYOUT WEBHOOK
# ==============================
# [SECURITY AUDIT] CSRF exemption is safe here because we perform mandatory 
# HMAC-SHA256 signature verification. This ensures the request is genuine 
# from Razorpay and prevents CSRF/forgery attacks.
@csrf_exempt
@require_POST
@idempotent_webhook("razorpay")
def payout_webhook(request):
    signature = request.headers.get("X-Razorpay-Signature")
    body = request.body

    # [SECURITY AUDIT] Ensure webhook secret is configured before attempting verification
    if not getattr(settings, "RAZORPAY_PAYOUT_WEBHOOK_SECRET", None):
        import logging
        logging.getLogger(__name__).critical("RAZORPAY_PAYOUT_WEBHOOK_SECRET missing")
        return HttpResponse(status=500)

    if not verify_razorpay_payout_webhook(body=body, signature=signature):
        return HttpResponse(status=400)

    payload = json.loads(body)

    event_id = payload.get("id")
    event_type = payload.get("event")

    entity = payload.get("payload", {}).get("payout", {}).get("entity", {})
    reference = entity.get("reference_id")
    status = entity.get("status")

    if not all([event_id, event_type, reference, status]):
        return HttpResponse(status=400)

    # 🔒 IDENTITY GATE
    if not register_webhook_event(
        provider="razorpay",
        event_id=event_id,
        event_type=event_type,
        raw_body=body,
    ):
        return HttpResponse(status=200)

    payout = Payout.objects.filter(reference=reference).first()
    if not payout:
        return HttpResponse(status=200)

    with transaction.atomic():
        if status == "processed":
            mark_payout_success(payout=payout)
        elif status in {"failed", "reversed"}:
            mark_payout_failed(payout=payout)

    return HttpResponse(status=200)
