import json
import hmac
import hashlib
from decimal import Decimal
from django.urls import reverse
from django.conf import settings

from apps.payments.models import Payment, LedgerEntry


def sign(body: bytes):
    return hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()


def test_payment_captured_webhook_idempotent(client, user):
    payment = Payment.objects.create(
        user=user,
        ride_id=1,
        amount=Decimal("100.00"),
        gateway_order_id="order_123",
    )

    payload = {
        "id": "evt_123",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": "order_123",
                    "amount": 10000,
                }
            }
        },
    }

    body = json.dumps(payload).encode()
    signature = sign(body)

    url = reverse("payments:razorpay-webhook")

    # first call
    r1 = client.post(
        url,
        data=body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=signature,
    )
    assert r1.status_code == 200

    # replay attack
    r2 = client.post(
        url,
        data=body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=signature,
    )
    assert r2.status_code == 200

    payment.refresh_from_db()
    assert payment.status == Payment.Status.CAPTURED

    # Ledger entry created ONCE
    assert LedgerEntry.objects.filter(
        reference=f"payment:{payment.id}"
    ).count() == 1
