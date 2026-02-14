import json
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.urls import reverse

from apps.payments.models import Payout, LedgerEntry


def sign(body):
    return hmac.new(
        settings.RAZORPAY_PAYOUT_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()


from django.test import override_settings

@override_settings(RAZORPAY_PAYOUT_WEBHOOK_SECRET="test_secret")
def test_payout_success_webhook(client, driver, platform_user):
    # Fund the driver first
    LedgerEntry.objects.create(
        user=driver,
        amount=Decimal("1000.00"),
        entry_type=LedgerEntry.Type.CREDIT,
        reason=LedgerEntry.Reason.DRIVER_EARNING,
    )

    payout = Payout.objects.create(
        driver=driver,
        amount=Decimal("500.00"),
        fee=Decimal("10.00"),
        net_amount=Decimal("490.00"),
        status=Payout.Status.PROCESSING,
        reference="payout:test:1",
    )

    LedgerEntry.objects.create(
        user=driver,
        amount=Decimal("500.00"),
        entry_type=LedgerEntry.Type.HOLD,
        reference=f"hold:{payout.reference}",
    )

    payload = {
        "id": "evt_payout_123",
        "event": "payout.processed",
        "payload": {
            "payout": {
                "entity": {
                    "reference_id": payout.reference,
                    "status": "processed",
                }
            }
        }
    }

    body = json.dumps(payload).encode()
    signature = sign(body)

    url = reverse("payments:payout-webhook")

    r = client.post(
        url,
        data=body,
        content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=signature,
    )
    assert r.status_code == 200

    payout.refresh_from_db()
    assert payout.status == Payout.Status.PAID

    # Debit happened
    assert LedgerEntry.objects.filter(
        user=driver,
        entry_type=LedgerEntry.Type.DEBIT,
        reference__contains=payout.reference,
    ).exists()
