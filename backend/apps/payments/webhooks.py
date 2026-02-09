import hmac
import hashlib
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction

from apps.payments.models import Payment, LedgerEntry


@csrf_exempt
def razorpay_webhook(request):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    body = request.body
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        return HttpResponse(status=400)

    expected = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return HttpResponse(status=400)

    payload = json.loads(body)
    event = payload.get("event")

    if event != "payment.captured":
        return HttpResponse(status=200)

    payment_entity = payload["payload"]["payment"]["entity"]
    order_id = payment_entity["order_id"]
    payment_id = payment_entity["id"]
    amount = payment_entity["amount"] / 100

    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(
            gateway_order_id=order_id
        ).first()

        if not payment or payment.status == Payment.Status.CAPTURED:
            return HttpResponse(status=200)

        payment.gateway_payment_id = payment_id
        payment.status = Payment.Status.CAPTURED
        payment.save()

        LedgerEntry.objects.create(
            user=payment.user,
            ride_id=payment.ride_id,
            amount=amount,
            entry_type=LedgerEntry.Type.DEBIT,
            reference=payment_id,
        )

    return HttpResponse(status=200)
