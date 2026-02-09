import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.payments.services.razorpay import verify_signature
from apps.payments.services.ledger import debit
from apps.rides.models import Ride


@csrf_exempt
def razorpay_webhook(request):
    payload = json.loads(request.body)
    signature = request.headers.get("X-Razorpay-Signature")

    verify_signature({
        "razorpay_order_id": payload["payload"]["payment"]["entity"]["order_id"],
        "razorpay_payment_id": payload["payload"]["payment"]["entity"]["id"],
        "razorpay_signature": signature,
    })

    payment = payload["payload"]["payment"]["entity"]
    ride_id = int(payment["notes"]["ride_id"])

    ride = Ride.objects.get(id=ride_id)

    debit(
        user=ride.rider,
        ride_id=ride.id,
        amount=ride.final_fare,
        reference=payment["id"],
    )

    return HttpResponse(status=200)
